import os, time
import bpy
from . import CiderMeshes, CiderMaterial
from Cider.CiderUtils import cider_path_getter, cider_path_setter

_BRIDGE = None
_PIPELINE_PARAMETERS = None
_TIMESTAMP = time.time()

def is_cider_active():
    return bpy.context.scene.cider.enabled

def get_bridge(scene=None, force_creation=False):
    global _BRIDGE
    bridge = _BRIDGE
    if (bridge and bridge.lost_connection) or (bridge is None and force_creation):
        _BRIDGE = None
        if is_cider_active() == False:
            return None
        if scene is None:
            scene = bpy.context.scene
        scene.cider.update_pipeline(bpy.context)
    return _BRIDGE

# def sync_pipeline_settings(default_world=None):
#     for scene in bpy.data.scenes:
#         if scene.cider.enabled and scene.world is None:
#             scene.world = bpy.data.worlds.new(f'{scene.name} World')
#             setup_parameters([scene.world])
#     if default_world is None:
#         default_world = bpy.data.worlds[0]
#     for world in bpy.data.worlds:
#         if world.cider.pipeline != default_world.cider.pipeline:
#             world.cider.pipeline = default_world.cider.pipeline
#         if world.cider.viewport_bit_depth != default_world.cider.viewport_bit_depth:
#             world.cider.viewport_bit_depth = default_world.cider.viewport_bit_depth

_ON_PIPELINE_SETTINGS_UPDATE = False

class CiderPipeline(bpy.types.PropertyGroup):
    def update_pipeline(self, context):
        global _TIMESTAMP
        _TIMESTAMP = time.time()
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        pipeline = os.path.join(current_dir,'LinePipeline.py')
        
        path = bpy.path.abspath(pipeline, library=self.id_data.library)
        import Bridge
        bridge = Bridge.Client_API.Bridge(path, int(self.viewport_bit_depth), True, None, [], None)
        from Malt.Utils import LOG
        LOG.info('Blender {} {} {}'.format(bpy.app.version_string, bpy.app.build_branch, bpy.app.build_hash))
        params = bridge.get_parameters()

        global _BRIDGE, _PIPELINE_PARAMETERS
        _BRIDGE = bridge
        _PIPELINE_PARAMETERS = params
        
        #CiderMaterial.reset_materials()
        CiderMeshes.reset_meshes()

        self.setup_line_presets()
        
        #TODO: This can fail depending on the current context, ID classes might not be writeable
        setup_all_ids()

    def update_pipeline_settings(self, context):
        global _ON_PIPELINE_SETTINGS_UPDATE
        if _ON_PIPELINE_SETTINGS_UPDATE:
            return
        _ON_PIPELINE_SETTINGS_UPDATE = True

        #sync_pipeline_settings(self.id_data)
        
        _ON_PIPELINE_SETTINGS_UPDATE = False
        
        self.update_pipeline(context)

    enabled: bpy.props.BoolProperty(name='Enable Cider', default=False)
    display_viewport: bpy.props.BoolProperty(name='Viewport Display', default=True)
    pipeline : bpy.props.StringProperty(name="Cider Pipeline", subtype='FILE_PATH', update=update_pipeline_settings, set=cider_path_setter('pipeline'), get=cider_path_getter('pipeline'))
    viewport_bit_depth : bpy.props.EnumProperty(items=[('8', '8', ''),('16', '16', ''),('32', '32', '')], name="Bit Depth (Viewport)", update=update_pipeline_settings)
    overrides : bpy.props.StringProperty(name='Pipeline Overrides', default='Preview,Final Render')
    line_presets : bpy.props.CollectionProperty(name='Line Settings', type=CiderMaterial.CiderLinePreset)

    def setup_line_presets(self):
        if not self.line_presets:
            setting = self.line_presets.add()
            setting.name = "Default"

    def draw_header(self, layout):
        layout.prop(self, 'enabled', text="")

    def draw_ui(self, layout):
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, 'viewport_bit_depth')


class OT_CiderReloadPipeline(bpy.types.Operator):
    bl_idname = "wm.cider_reload_pipeline"
    bl_label = "Cider Reload Pipeline"

    @classmethod
    def poll(cls, context):
        return context.scene.cider.enabled

    def execute(self, context):
        import Bridge
        Bridge.reload()
        context.scene.cider.update_pipeline(context)
        return {'FINISHED'}

class CIDER_PT_Pipeline(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    bl_context = "render"
    bl_label = "Cider"

    def draw_header(self,context):
        context.scene.cider.draw_header(self.layout)
    
    def draw(self, context):
        context.scene.cider.draw_ui(self.layout)

class VIEW3D_PT_Cider(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "View"
    bl_label = "Cider"

    @classmethod
    def poll(cls, context):
        return context.scene.cider.enabled and context.space_data.shading.type == 'RENDERED'

    def draw(self, context):
        stats = CiderPipeline.get_bridge().get_stats()
        for line in stats.splitlines():
            self.layout.label(text=line)

classes = (
    CiderPipeline,
    OT_CiderReloadPipeline,
    CIDER_PT_Pipeline,
    VIEW3D_PT_Cider
)

def setup_all_ids():
    setup_parameters(bpy.data.scenes)
    setup_parameters(bpy.data.worlds)
    setup_parameters(bpy.data.cameras)
    setup_parameters(bpy.data.objects)
    setup_parameters(bpy.data.materials)
    setup_parameters(bpy.data.meshes)
    setup_parameters(bpy.data.curves)
    setup_parameters(bpy.data.metaballs)
    setup_parameters(bpy.data.lights)

def setup_parameters(ids):
    global _PIPELINE_PARAMETERS
    pipeline_parameters = _PIPELINE_PARAMETERS

    class_parameters_map = {
        bpy.types.Scene : pipeline_parameters.scene,
        bpy.types.World : pipeline_parameters.world,
        bpy.types.Camera : pipeline_parameters.camera,
        bpy.types.Object : pipeline_parameters.object,
        bpy.types.Material : pipeline_parameters.material,
        bpy.types.Mesh : pipeline_parameters.mesh,
        bpy.types.Curve : pipeline_parameters.mesh,
        bpy.types.MetaBall : pipeline_parameters.mesh,
        bpy.types.Light : pipeline_parameters.light,
    }

    for bid in ids:
        for cls, parameters in class_parameters_map.items():
            if isinstance(bid, cls):
                bid.cider_parameters.setup(parameters)

_ON_DEPSGRAPH_UPDATE = False

@bpy.app.handlers.persistent
def depsgraph_update(scene, depsgraph):
    global _BRIDGE, _ON_DEPSGRAPH_UPDATE

    if _ON_DEPSGRAPH_UPDATE:
        return
    _ON_DEPSGRAPH_UPDATE = True
    try:
        if is_cider_active() == False:
            _BRIDGE = None
            return
        
        #sync_pipeline_settings()

        if _BRIDGE is None:
            scene.cider.update_pipeline(bpy.context)
            return

        ids = []
        class_data_map = {
            bpy.types.Scene : bpy.data.scenes,
            bpy.types.World : bpy.data.worlds,
            bpy.types.Camera : bpy.data.cameras,
            bpy.types.Object : bpy.data.objects,
            bpy.types.Material : bpy.data.materials,
            bpy.types.Mesh : bpy.data.meshes,
            bpy.types.Curve : bpy.data.curves,
            bpy.types.MetaBall : bpy.data.metaballs,
            bpy.types.Light : bpy.data.lights,
        }
        for update in depsgraph.updates:
            # Try to avoid as much re-setups as possible. 
            # Ideally we would do it only on ID creation.
            if update.is_updated_geometry == True or update.is_updated_transform == False:
                for cls, data in class_data_map.items():
                    if isinstance(update.id, cls):
                        ids.append(data[update.id.name])
        setup_parameters(ids)

        redraw = False
        for update in depsgraph.updates:
            if update.is_updated_geometry:
                if isinstance(update.id, bpy.types.Object):
                    CiderMeshes.unload_mesh(update.id)
        if redraw:
            for screen in bpy.data.screens:
                for area in screen.areas:
                    area.tag_redraw()
    except:
        import traceback
        traceback.print_exc()
    finally:
        _ON_DEPSGRAPH_UPDATE = False

@bpy.app.handlers.persistent
def load_scene(dummy1=None,dummy2=None):
    global _BRIDGE
    _BRIDGE = None

@bpy.app.handlers.persistent
def load_scene_post(dummy1=None,dummy2=None):
    if is_cider_active():
        bpy.context.scene.cider.update_pipeline(bpy.context)

__SAVE_PATH = None
@bpy.app.handlers.persistent
def save_pre(dummy1=None,dummy2=None):
    global __SAVE_PATH
    __SAVE_PATH = bpy.data.filepath

@bpy.app.handlers.persistent
def save_post(dummy1=None,dummy2=None):
    if __SAVE_PATH != bpy.data.filepath:
        load_scene_post()

def track_pipeline_changes():
    if is_cider_active() == False:
        return 1
    try:
        scene = bpy.context.scene
        cider = scene.cider
        path = bpy.path.abspath(cider.pipeline, library=cider.id_data.library)
        if os.path.exists(path):
            stats = os.stat(path)
            if stats.st_mtime > _TIMESTAMP:
                cider.update_pipeline(bpy.context)
    except:
        import traceback
        print(traceback.format_exc())

    return 1

def register():
    for _class in classes: bpy.utils.register_class(_class)
    bpy.types.Scene.cider = bpy.props.PointerProperty(type=CiderPipeline)
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update)
    bpy.app.handlers.load_pre.append(load_scene)
    bpy.app.handlers.load_post.append(load_scene_post)
    bpy.app.handlers.save_pre.append(save_pre)
    bpy.app.handlers.save_post.append(save_post)
    bpy.app.timers.register(track_pipeline_changes, persistent=True)
    
def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)
    del bpy.types.Scene.cider
    bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update)
    bpy.app.handlers.load_pre.remove(load_scene)
    bpy.app.handlers.load_post.remove(load_scene_post)
    bpy.app.handlers.save_pre.remove(save_pre)
    bpy.app.handlers.save_post.remove(save_post)
    bpy.app.timers.unregister(track_pipeline_changes)
