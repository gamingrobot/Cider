from Malt.GL.GL import *
from Malt.GL.RenderTarget import RenderTarget
from Malt.GL.Texture import Texture
from Malt.Scene import TextureShaderResource
from Malt.Pipeline import *
from Malt.Render import Sampling

class LinePipeline(Pipeline):

    DEFAULT_SHADER = None
    
    def __init__(self, plugins=[]):
        shader_dir = path.join(path.dirname(__file__), 'Shaders')
        if shader_dir not in self.SHADER_INCLUDE_PATHS:
            self.SHADER_INCLUDE_PATHS.append(shader_dir)
        self.sampling_grid_size = 1
        self.samples = None
        super().__init__(plugins)

    def compile_material_from_source(self, source):
        return {
            'PRE_PASS' : self.compile_shader_from_source(source, [], ['PRE_PASS']),
            'MAIN_PASS' : self.compile_shader_from_source(source, [], ['MAIN_PASS']),
            'LINE_PASS' : self.compile_shader_from_source(source, [], ['LINE_PASS']),
        }

    def copy_default_shader(self):
        return {
            'PRE_PASS' : LinePipeline.DEFAULT_SHADER['PRE_PASS'],
            'MAIN_PASS' : LinePipeline.DEFAULT_SHADER['MAIN_PASS'].copy(),
            'LINE_PASS' : LinePipeline.DEFAULT_SHADER['LINE_PASS'],
        }
    
    def setup_parameters(self):
        self.parameters = PipelineParameters()
        
        self.parameters.object['visible'] = Parameter(True, Type.BOOL, doc=
            "Disables object visibility, so object is not rendered.")

        self.parameters.mesh['double_sided'] = Parameter(False, Type.BOOL, doc=
            "Disables backface culling, so geometry is rendered from both sides.")
        
        self.parameters.mesh['precomputed_tangents'] = Parameter(False, Type.BOOL, doc="""
            Load precomputed mesh tangents *(needed for improving normal mapping quality on low poly meshes)*. 
            It's disabled by default since it slows down mesh loading in Blender.  
            When disabled, the *tangents* are calculated on the fly from the *pixel shader*.""")

        self.parameters.scene['samples.grid_size'] = Parameter(8, Type.INT, doc="""
            The number of render samples per side in the sampling grid. 
            The total number of samples is the square of this value minus the samples that fall outside the sampling radius.  
            Higher values will provide cleaner renders at the cost of increased render times.""")
        
        self.parameters.scene['samples.grid_size@Preview'] = Parameter(4, Type.INT)
        
        self.parameters.scene['samples.width'] = Parameter(1.0, Type.FLOAT, doc="""
            The width (and height) of the sampling grid. 
            Larger values will result in smoother/blurrier images while lower values will result in sharper/more aliased ones. 
            Keep it withing the 1-2 range for best results.""")
        
        # Cider maps parameters.material to FreestyleLineStyle but will show up in the material panel
        self.parameters.material['line.color'] = Parameter((0.0,0.0,0.0,1.0), Type.FLOAT, size=4, doc="Width Units")
        self.parameters.material['line.width_scale'] = Parameter(2.0, Type.FLOAT, doc="Width Scale")
        self.parameters.material['line.width_units'] = EnumParameter(['Pixel', 'Screen', 'World'], 'Pixel', Type.ENUM, doc="Width Units")
        self.parameters.material['line_depth.width'] = Parameter(1.0, Type.FLOAT, doc="Depth Width")
        self.parameters.material['line_depth.threshold'] = Parameter(0.1, Type.FLOAT, doc="Depth Threshold")
        self.parameters.material['line_depth.threshold_range'] = Parameter(0.0, Type.FLOAT, doc="Depth Threshold Range")
        self.parameters.material['line_normal.width'] = Parameter(1.0, Type.FLOAT, doc="Normal Width")
        self.parameters.material['line_normal.threshold'] = Parameter(0.5, Type.FLOAT, doc="Normal Threshold")
        self.parameters.material['line_normal.threshold_range'] = Parameter(0.0, Type.FLOAT, doc="Normal Threshold Range")
        self.parameters.material['line_object.boundary_width'] = Parameter(1.0, Type.FLOAT, doc="Object Boundary Width")


    def setup_resources(self):
        super().setup_resources()
        if LinePipeline.DEFAULT_SHADER is None: 
            LinePipeline.DEFAULT_SHADER = self.compile_material_from_source('#include "LineShader.glsl"')
    
        self.default_shader = LinePipeline.DEFAULT_SHADER
    
    def get_samples(self):
        if self.samples is None:
            self.samples = Sampling.get_RGSS_samples(self.sampling_grid_size, 1.0)
        return self.samples
    
    def get_sample(self, width):
        w, h = self.get_samples()[self.sample_count]
        w*=width
        h*=width
        return w, h

    def setup_render_targets(self, resolution):
        self.t_depth = Texture(resolution, GL_DEPTH_COMPONENT32F)
        self.t_normal_depth = Texture(resolution, GL_RGBA32F)
        self.t_id = Texture(resolution, GL_RGBA16UI, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.fbo_prepass = RenderTarget([self.t_normal_depth, self.t_id], self.t_depth)
        self.t_linecolor = Texture(resolution, GL_RGBA16F)
        self.t_linewidth = Texture(resolution, GL_R16F)
        self.fbo_mainpass = RenderTarget([self.t_linecolor, self.t_linewidth], self.t_depth)
        self.t_line = Texture(resolution, GL_RGBA16F)
        self.fbo_linepass = RenderTarget([self.t_line])
        self.t_aa = Texture(resolution, GL_RGBA16F)
        self.fbo_aa = RenderTarget([self.t_aa])

    def do_render(self, resolution, scene, is_final_render, is_new_frame):        
        if self.sampling_grid_size != scene.parameters['samples.grid_size']:
            self.sampling_grid_size = scene.parameters['samples.grid_size']
            self.samples = None

        sample_offset = self.get_sample(scene.parameters['samples.width'])

        # Setup material shaders
        for material in scene.batches.keys():
            material.shader = self.copy_default_shader()
            for shader in material.shader.values():
                if 'IN_LINE_COLOR' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_COLOR'].set_value(material.parameters['line.color'])
                if 'IN_LINE_WIDTH_SCALE' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_WIDTH_SCALE'].set_value(material.parameters['line.width_scale'])
                if 'IN_LINE_WIDTH_UNITS' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_WIDTH_UNITS'].set_value(material.parameters['line.width_units'])
                    #shader.uniforms['IN_LINE_WIDTH_UNITS'].set_value(0)
                if 'IN_LINE_DEPTH_WIDTH' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_DEPTH_WIDTH'].set_value(material.parameters['line_depth.width'])
                if 'IN_LINE_DEPTH_THRESHOLD' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_DEPTH_THRESHOLD'].set_value(material.parameters['line_depth.threshold'])
                if 'IN_LINE_DEPTH_THRESHOLD_RANGE' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_DEPTH_THRESHOLD_RANGE'].set_value(material.parameters['line_depth.threshold_range'])
                if 'IN_LINE_NORMAL_WIDTH' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_NORMAL_WIDTH'].set_value(material.parameters['line_normal.width'])
                if 'IN_LINE_NORMAL_THRESHOLD' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_NORMAL_THRESHOLD'].set_value(material.parameters['line_normal.threshold'])
                if 'IN_LINE_NORMAL_THRESHOLD_RANGE' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_NORMAL_THRESHOLD_RANGE'].set_value(material.parameters['line_normal.threshold_range'])
                if 'IN_LINE_OBJECT_THRESHOLD_RANGE' in shader.uniforms.keys():
                    shader.uniforms['IN_LINE_OBJECT_THRESHOLD_RANGE'].set_value(material.parameters['line_object.boundary_width'])
        
        self.common_buffer.load(scene, resolution, sample_offset, self.sample_count)
        shader_resources = { 'COMMON_UNIFORMS' : self.common_buffer }

        # Pre
        self.fbo_prepass.clear([(0,0,0,1), (0,0,0,0)], 1)
        self.draw_scene_pass(self.fbo_prepass, scene.batches, 'PRE_PASS', None, shader_resources)
        
        # Main
        self.fbo_mainpass.clear([(0,0,0,0), (0)])
        shader_resources['IN_NORMAL_DEPTH'] = TextureShaderResource('IN_NORMAL_DEPTH', self.t_normal_depth)
        shader_resources['IN_ID'] = TextureShaderResource('IN_ID', self.t_id)
        self.draw_scene_pass(self.fbo_mainpass, scene.batches, 'MAIN_PASS', None, shader_resources)

        # Line
        self.fbo_linepass.clear()
        line_pass = self.default_shader['LINE_PASS']
        line_pass.textures['IN_NORMAL_DEPTH'] = self.t_normal_depth
        line_pass.textures['IN_ID'] = self.t_id
        line_pass.textures['IN_COLOR'] = self.t_linecolor
        line_pass.textures['IN_WIDTH'] = self.t_linewidth
        self.common_buffer.shader_callback(line_pass)
        self.draw_screen_pass(line_pass, self.fbo_linepass) 

        # SSAA
        if is_new_frame:
            self.fbo_aa.clear([(0,0,0,0)])
        self.blend_texture(self.t_line, self.fbo_aa, 1.0 / (self.sample_count + 1))

        return { 'COLOR' : self.t_aa }



PIPELINE = LinePipeline
