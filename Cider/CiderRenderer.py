import ctypes, time, platform
import xxhash
import bpy
from Malt import Scene
from . import CiderPipeline, CiderMeshes
from . CiderUtils import is_cider_active
import gpu

CAPTURE = False

WINM = None
if platform.system() == 'Windows':
    WINM = ctypes.WinDLL('winmm')

def high_res_sleep(seconds):
    if WINM:
        WINM.timeBeginPeriod(1)
        time.sleep(seconds)
        WINM.timeEndPeriod(1)
    else:
        time.sleep(seconds)


class CiderRenderer:
    def __init__(self, *args, **kwargs):
        self.display_draw = None
        self.scene = Scene.Scene()
        self.view_matrix = None
        self.request_new_frame = True
        self.request_scene_update = True
        self.bridge = CiderPipeline.get_bridge()
        self.bridge_id = self.bridge.get_viewport_id() if self.bridge else None
        self.last_frame_time = 0

    def __del__(self):
        try:
            self.bridge.free_viewport_id(self.bridge_id)
            self.bridge = None
        except:
            # Sometimes Blender seems to call the destructor on un-initialized instances (???)
            pass

    def get_scene(self, context, depsgraph, request_scene_update, overrides, viewport=False):
        if request_scene_update == True:
            scene = Scene.Scene()
            self.scene = scene
        scene = self.scene
        
        if hasattr(scene, 'proxys') == False:
            scene.proxys = {}

        scene.parameters = depsgraph.scene_eval.cider_parameters.get_parameters(overrides, scene.proxys)

        scene.frame = depsgraph.scene_eval.frame_current
        r = depsgraph.scene_eval.render
        fps = r.fps / r.fps_base
        remap = r.frame_map_new / r.frame_map_old
        scene.time = (scene.frame / fps) * remap
        
        def flatten_matrix(matrix):
            return [e for v in matrix.transposed() for e in v]
        
        #Camera
        if viewport:
            view_3d = context.region_data 
            camera_matrix = flatten_matrix(view_3d.view_matrix)
            projection_matrix = flatten_matrix(view_3d.window_matrix)
            if view_3d.perspective_matrix != self.view_matrix:
                self.view_matrix = view_3d.perspective_matrix.copy()
                self.request_new_frame = True
            scene.camera = Scene.Camera(camera_matrix, projection_matrix)
        else:
            camera = depsgraph.scene_eval.camera
            camera_matrix = flatten_matrix(camera.matrix_world.inverted())
            projection_matrix = flatten_matrix(
                camera.calc_matrix_camera( depsgraph, 
                    x=depsgraph.scene_eval.render.resolution_x, 
                    y=depsgraph.scene_eval.render.resolution_y
            ))
            scene.camera = Scene.Camera(camera_matrix, projection_matrix)
        
        if request_scene_update == False:
            return scene
        

        def get_line_style_proxy(line_style):
            name = line_style.name_full
            key = ('material',name)
            if key not in scene.proxys.keys():
                parameters = line_style.cider_parameters.get_parameters(overrides, scene.proxys)
                from Bridge.Proxys import MaterialProxy
                scene.proxys[key]  = MaterialProxy('', {}, parameters)
            return scene.proxys[key]

        meshes = {}

        #Objects
        def add_object(obj, matrix, id):
            if obj.type in ('MESH','CURVE','SURFACE','META', 'FONT'):
                name = CiderMeshes.get_mesh_name(obj)
                if not viewport:
                    name = '___F12___' + name
                
                if name not in meshes:
                    # (Uses obj.original) Malt Parameters are not present in the evaluated mesh
                    parameters = obj.original.data.cider_parameters.get_parameters(overrides, scene.proxys)
                    cider_mesh = None
                    
                    if viewport:
                        cider_mesh = CiderMeshes.get_mesh(obj)
                    else: #always load the mesh for final renders
                        cider_mesh = CiderMeshes.load_mesh(obj, name)
                    
                    if cider_mesh:
                        meshes[name] = [Scene.Mesh(submesh, parameters) for submesh in cider_mesh]
                        for i, mesh in enumerate(meshes[name]):
                            scene.proxys[('mesh',name,i)] = mesh.mesh
                    else:
                        meshes[name] = None

                mesh = meshes[name]
                if mesh is None:
                    return
                
                scale = matrix.to_scale()
                mirror_scale = scale[0]*scale[1]*scale[2] < 0.0
                matrix = flatten_matrix(matrix)

                obj_parameters = obj.cider_parameters.get_parameters(overrides, scene.proxys)
                obj_parameters['ID'] = id

                # Remove objects marked not visible
                if 'visible' in obj_parameters and not obj_parameters['visible']:
                    return

                tags = set(collection.name for collection in obj.original.users_collection)

                scene_line_style = context.scene.cider.default_line_style
                default_line_style = get_line_style_proxy(scene_line_style)

                if len(obj.material_slots) > 0:
                    for i, slot in enumerate(obj.material_slots):
                        line_style = default_line_style
                        if slot.material and slot.material.cider.line_style:
                            line_style = get_line_style_proxy(slot.material.cider.line_style)
                        result = Scene.Object(matrix, mesh[i], line_style, obj_parameters, mirror_scale, tags)
                        scene.objects.append(result)
                else:
                    line_style = default_line_style
                result = Scene.Object(matrix, mesh[0], line_style, obj_parameters, mirror_scale, tags)
                scene.objects.append(result)

        is_f12 = not viewport

        def visible_display(obj):
            return obj.display_type in ('TEXTURED','SOLID')

        for obj in depsgraph.objects:
            if is_f12 or (visible_display(obj) and obj.visible_in_viewport_get(context.space_data)):
                id = xxhash.xxh3_64_intdigest(obj.name_full.encode()) % (2**16)
                add_object(obj, obj.matrix_world, id)

        for instance in depsgraph.object_instances:
            if instance.instance_object:
                obj = instance.instance_object
                parent = instance.parent
                if is_f12 or (visible_display(obj) and visible_display(parent) and
                parent.visible_in_viewport_get(context.space_data)):
                    id = abs(instance.random_id) % (2**16)
                    add_object(instance.instance_object, instance.matrix_world, id)
        
        return scene

    def render(self, context, depsgraph):
        scene = depsgraph.scene_eval
        scale = scene.render.resolution_percentage / 100.0

        self.size_x = int(scene.render.resolution_x * scale)
        self.size_y = int(scene.render.resolution_y * scale)
        resolution = (self.size_x, self.size_y)

        overrides = ['Final Render']

        bridge = CiderPipeline.get_bridge(depsgraph.scene, True)
        if self.bridge is not bridge:
            self.bridge = bridge
            self.bridge_id = self.bridge.get_viewport_id()
        

        scene = self.get_scene(context, depsgraph, True, overrides)
        self.bridge.render(0, resolution, scene, True, AOVs={})

        buffers = None
        finished = False

        import time
        while not finished:
            buffers, finished, read_resolution = self.bridge.render_result(0)
            time.sleep(0.1)
            if finished: break
        
        size = self.size_x * self.size_y

        from itertools import chain
        for output in self.bridge.render_outputs.keys():
            if output not in ('COLOR', 'DEPTH'):
                self.add_pass(output, 4, 'RGBA')
        

        name = f"Cider_{depsgraph.scene.name}_{depsgraph.view_layer.name}"
        image = bpy.data.images.get(name, None)
        if image is None:
            image = bpy.data.images.new(
                name,
                width=self.size_x,
                height=self.size_y,
                alpha=True,
                float_buffer=True
            )
            image.generated_color = [0, 0, 0, 0]
        if image.source != "GENERATED":
            image.source = "GENERATED"
        if not image.use_generated_float:
            image.use_generated_float = True
        image.colorspace_settings.name = "Linear Rec.709"
        if image.alpha_mode != "PREMUL":
            image.alpha_mode = "PREMUL"
        if image.size[0] != self.size_x or image.size[1] != self.size_y:
            image.scale(image.size[0] if self.size_x <= 0 else self.size_x, image.size[1] if self.size_y <= 0 else self.size_y)

        pixels = buffers["COLOR"]
        data_size = len(pixels)
        image.pixels = (ctypes.c_float * data_size).from_address(pixels._buffer.data)
        image.pack()

        # Delete the scene. Otherwise we get memory leaks.
        del self.scene


    def view_update(self):
        self.request_new_frame = True
        self.request_scene_update = True

    def view_draw(self, context, depsgraph):
        if self.bridge is not CiderPipeline.get_bridge():
            #The Bridge has been reset
            self.bridge = CiderPipeline.get_bridge()
            self.bridge_id = self.bridge.get_viewport_id()
            self.request_new_frame = True
            self.request_scene_update = True
        
        global CAPTURE
        if CAPTURE:
            self.request_new_frame = True
        
        overrides = []
        if context.space_data.shading.type == 'MATERIAL':
            overrides.append('Preview')

        scene = self.get_scene(context, depsgraph, self.request_scene_update, overrides, viewport=True)
        viewport_resolution = context.region.width, context.region.height
        resolution = viewport_resolution

        if self.request_new_frame:
            self.bridge.render(self.bridge_id, resolution, scene, self.request_scene_update, CAPTURE)
            CAPTURE = False
            self.request_new_frame = False
            self.request_scene_update = False
        
        target_fps = context.preferences.addons['Cider'].preferences.render_fps_cap
        if target_fps > 0:
            delta_time = time.perf_counter() - self.last_frame_time
            target_delta = 1.0 / target_fps
            if delta_time < target_delta:
                high_res_sleep(target_delta - delta_time)
        
        self.last_frame_time = time.perf_counter() 

        buffers, finished, read_resolution = self.bridge.render_result(self.bridge_id)
        pixels = buffers['COLOR']

        if not finished:
            context.area.tag_redraw()
        if pixels is None or resolution != read_resolution:
            # Only render if resolution is the same as read_resolution.
            # This avoids visual glitches when the viewport is resizing.
            # The alternative would be locking when writing/reading the pixel buffer.
            return
        
        for region in context.area.regions:
            if region.type == 'UI':
                region.tag_redraw()

        global DISPLAY_DRAW
        data_size = len(pixels)
        w,h = resolution
        if self.bridge.viewport_bit_depth == 8:
            data_size = data_size // 4
            h = h // 4
        elif self.bridge.viewport_bit_depth == 16:
            data_size = data_size // 2
            h = h // 2
        data_format = 'FLOAT' #Pretend we are uploading float data, since it's the only supported format.
        texture_format = 'RGBA32F'
        data_as_float = (ctypes.c_float * data_size).from_address(pixels._buffer.data)
        buffer = gpu.types.Buffer(data_format, data_size, data_as_float)
        render_texture = gpu.types.GPUTexture((w, h), format=texture_format, data=buffer)

        if DISPLAY_DRAW is None:
            DISPLAY_DRAW = DisplayDrawGPU()
        DISPLAY_DRAW.draw(self.bridge.viewport_bit_depth, resolution, render_texture)


DISPLAY_DRAW = None

class DisplayDrawGPU():    
    def __init__(self):
        import gpu
        from gpu_extras.batch import batch_for_shader

        vertex_src = """
        void main()
        {
            IO_POSITION = IN_POSITION * vec3(1000, 1000, 0.5);
            gl_Position = vec4(IO_POSITION, 1);
        }
        """

        pixel_src = """
        vec3 srgb_to_linear(vec3 srgb)
        {
            vec3 low = srgb / 12.92;
            vec3 high = pow((srgb + 0.055)/1.055, vec3(2.4));
            return mix(low, high, greaterThan(srgb, vec3(0.04045)));
        }

        void main()
        {
            vec2 uv =  IO_POSITION.xy * 0.5 + 0.5;

            int divisor = 32 / bit_depth;

            ivec2 output_texel = ivec2(vec2(output_res) * uv);
            int output_texel_linear = output_texel.y * output_res.x + output_texel.x;
            
            int texel_linear_read = output_texel_linear / divisor;
            ivec2 texel_read = ivec2(texel_linear_read % output_res.x, texel_linear_read / output_res.x);
            int sub_texel_index = output_texel_linear % divisor;

            vec4 texel_value = texelFetch(input_texture, texel_read, 0);

            if(bit_depth == 32)
            {
                OUT_COLOR = texel_value;
            }
            else if(bit_depth == 16)
            {
                vec2 sub_texel_value = sub_texel_index == 0 ? texel_value.xy : texel_value.zw;

                uint packed_xy = floatBitsToUint(sub_texel_value.x);
                uint packed_yz = floatBitsToUint(sub_texel_value.y);

                OUT_COLOR.rg = unpackHalf2x16(packed_xy);
                OUT_COLOR.ba = unpackHalf2x16(packed_yz);
            }
            else if(bit_depth == 8)
            {
                float sub_texel_value = texel_value[sub_texel_index];
                uint packed_value = floatBitsToUint(sub_texel_value);
                OUT_COLOR = unpackUnorm4x8(packed_value);
                OUT_COLOR.rgb = srgb_to_linear(OUT_COLOR.rgb);
            }
            else{
                OUT_COLOR = vec4(1,1,0,1);
            }
        }
        """

        self.iface = gpu.types.GPUStageInterfaceInfo("IFace")
        self.iface.smooth('VEC3', "IO_POSITION")
        
        self.sh_info = gpu.types.GPUShaderCreateInfo()
        self.sh_info.push_constant('INT', "bit_depth")
        self.sh_info.push_constant('IVEC2', "output_res")
        self.sh_info.sampler(0, 'FLOAT_2D', "input_texture")
        self.sh_info.vertex_source(vertex_src)
        self.sh_info.vertex_in(0, 'VEC3', "IN_POSITION")
        self.sh_info.vertex_out(self.iface)
        self.sh_info.fragment_source(pixel_src)
        self.sh_info.fragment_out(0, 'VEC4', "OUT_COLOR")

        self.shader = gpu.shader.create_from_info(self.sh_info)

        positions=[
            ( 1.0,  1.0, 1.0),
            ( 1.0, -1.0, 1.0),
            (-1.0, -1.0, 1.0),
            (-1.0,  1.0, 1.0),
        ]
        indices=[
            (0, 1, 3),
            (1, 2, 3),
        ]
        
        self.quad = batch_for_shader(
            self.shader, 'TRIS',
            {"IN_POSITION": positions},
            indices=indices
        )

    def draw(self, bit_depth, resolution, texture):
        self.shader.bind()
        self.shader.uniform_int("bit_depth", bit_depth)
        self.shader.uniform_int("output_res", resolution)
        self.shader.uniform_sampler("input_texture", texture)
        gpu.state.blend_set("ALPHA")
        self.quad.draw(self.shader)
        gpu.state.blend_set("NONE")

_RENDERER = None

@bpy.app.handlers.persistent
def on_pre_render(scene: bpy.types.Scene):
    if is_cider_active():
        global _RENDERER
        if _RENDERER is None:
            _RENDERER = CiderRenderer()
        
        # TODO pull deps from viewlayers?
        depsgraph = bpy.context.evaluated_depsgraph_get()
        try:
            _RENDERER.render(bpy.context, depsgraph)
        except:
            raise

@bpy.app.handlers.persistent
def depsgraph_update(scene, depsgraph):
    if is_cider_active():
        global _RENDERER
        if _RENDERER is None:
            return

        try:
            _RENDERER.view_update()
        except:
            raise

def viewport_draw():
    if is_cider_active() and bpy.context.scene.cider.display_viewport and bpy.context.space_data.shading.type == 'RENDERED':
        global _RENDERER
        if _RENDERER is None:
            _RENDERER = CiderRenderer()
        
        depsgraph = bpy.context.evaluated_depsgraph_get()

        try:
            _RENDERER.view_draw(bpy.context, depsgraph)
        except:
            raise

classes = [
]

_VIEWPORT_DRAW_HANDLER = None

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update)
    bpy.app.handlers.render_pre.append(on_pre_render)
    global _VIEWPORT_DRAW_HANDLER
    _VIEWPORT_DRAW_HANDLER = bpy.types.SpaceView3D.draw_handler_add(viewport_draw, (), 'WINDOW', 'POST_PIXEL')


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update)
    bpy.app.handlers.render_pre.remove(on_pre_render)

    global _VIEWPORT_DRAW_HANDLER
    bpy.types.SpaceView3D.draw_handler_remove(_VIEWPORT_DRAW_HANDLER, 'WINDOW')

