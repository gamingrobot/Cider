import bpy
from . CiderUtils import CiderCallback
from pprint import pprint

class CiderLineStyle(bpy.types.PropertyGroup):
    number: bpy.props.IntProperty(name='Test', default=0)

    def draw_ui(self, layout):
        row = layout.row(align=True)
        row.label(text="Number")
        row.prop(self, "number", text="")

classes = (
    CiderLineStyle,
)    

def register():
    for _class in classes: bpy.utils.register_class(_class)
    bpy.types.FreestyleLineStyle.cider = bpy.props.PointerProperty(type=CiderLineStyle)

def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)
