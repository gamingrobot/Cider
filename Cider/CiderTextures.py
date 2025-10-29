import ctypes
from . import CiderPipeline

__TEXTURES = {}

def get_texture(texture):
    name = texture.name_full
    if name not in __TEXTURES or __TEXTURES[name] is None:
        __TEXTURES[name] = __load_texture(texture)
    return __TEXTURES[name]


def __load_texture(texture):
    w,h = texture.size
    channels = int(texture.channels)
    size = w*h*channels
    sRGB = texture.colorspace_settings.name == 'sRGB' and texture.is_float == False
    if size == 0:
        return False

    buffer = CiderPipeline.get_bridge().get_shared_buffer(ctypes.c_float, size)
    texture.pixels.foreach_get(buffer.as_np_array())
    
    CiderPipeline.get_bridge().load_texture(texture.name_full, buffer, (w,h), channels, sRGB)
    
    from Bridge.Proxys import TextureProxy
    return TextureProxy(texture.name_full)

def copy_color_ramp(old, new):
    new.color_mode = old.color_mode
    new.hue_interpolation = old.hue_interpolation
    new.interpolation = old.interpolation
    while len(new.elements) > len(old.elements):
        new.elements.remove(new.elements[len(new.elements)-1])
    for i, o in enumerate(old.elements):
        n = new.elements[i] if i < len(new.elements) else new.elements.new(o.position) 
        n.position = o.position
        n.color = o.color[:]
        n.alpha = o.alpha
    
def reset_textures():
    global __TEXTURES
    __TEXTURES = {}
    global __GRADIENTS
    __GRADIENTS = {}

def unload_texture(texture):
    __TEXTURES[texture.name_full] = None

def register():
    pass

def unregister():
    pass
