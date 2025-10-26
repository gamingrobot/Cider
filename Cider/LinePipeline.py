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
    
    def setup_parameters(self):
        super().setup_parameters()
        self.parameters.world['Samples.Grid Size'] = Parameter(8, Type.INT, doc="""
            The number of render samples per side in the sampling grid. 
            The total number of samples is the square of this value minus the samples that fall outside the sampling radius.  
            Higher values will provide cleaner renders at the cost of increased render times.""")
        
        self.parameters.world['Samples.Grid Size @ Preview'] = Parameter(4, Type.INT)
        
        self.parameters.world['Samples.Width'] = Parameter(1.0, Type.FLOAT, doc="""
            The width (and height) of the sampling grid. 
            Larger values will result in smoother/blurrier images while lower values will result in sharper/more aliased ones. 
            Keep it withing the 1-2 range for best results.""")

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
        self.fbo_mainpass = RenderTarget([self.t_linecolor, self.t_linewidth])
        self.t_line = Texture(resolution, GL_RGBA16F)
        self.fbo_linepass = RenderTarget([self.t_line])
        self.t_aa = Texture(resolution, GL_RGBA16F)
        self.fbo_aa = RenderTarget([self.t_aa])

    def do_render(self, resolution, scene, is_final_render, is_new_frame):        
        shader_resources = { 'COMMON_UNIFORMS' : self.common_buffer }

        # Pre
        self.fbo_prepass.clear([(0,0,0,1), (0,0,0,0)], 1)
        self.draw_scene_pass(self.fbo_prepass, scene.batches, 'PRE_PASS', self.default_shader['PRE_PASS'], shader_resources)
        
        # Main
        # TODO can this be a screenpass?
        self.fbo_mainpass.clear([(0,0,0,0), (0)])
        shader_resources['IN_NORMAL_DEPTH'] = TextureShaderResource('IN_NORMAL_DEPTH', self.t_normal_depth)
        shader_resources['IN_ID'] = TextureShaderResource('IN_ID', self.t_id)
        self.draw_scene_pass(self.fbo_mainpass, scene.batches, 'MAIN_PASS', self.default_shader['MAIN_PASS'], shader_resources)

        # Line
        self.fbo_linepass.clear()
        line_pass = self.default_shader['LINE_PASS']
        line_pass.textures['IN_NORMAL_DEPTH'] = self.t_normal_depth
        line_pass.textures['IN_ID'] = self.t_id
        line_pass.textures['IN_LINE_COLOR'] = self.t_linecolor
        line_pass.textures['IN_LINE_WIDTH'] = self.t_linewidth
        self.common_buffer.shader_callback(line_pass)
        self.draw_screen_pass(line_pass, self.fbo_linepass) 

        # SSAA
        if is_new_frame:
            self.fbo_aa.clear([(0,0,0,0)])
        self.blend_texture(self.t_line, self.fbo_aa, 1.0 / (self.sample_count + 1))

        return { 'COLOR' : self.t_aa }


PIPELINE = LinePipeline
