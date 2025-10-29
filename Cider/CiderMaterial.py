import bpy
from . CiderUtils import is_cider_active
from pprint import pprint

class CiderMaterial(bpy.types.PropertyGroup):    

    def linestyle_update(self, context):
        self.id_data.update_tag()
        self.line_style.update_tag()

    line_style: bpy.props.PointerProperty(name="LineStyle", type=bpy.types.FreestyleLineStyle, update=linestyle_update)

    def draw_ui(self, layout, context):
        layout.active = self.id_data.library is None #only local data can be edited
        row = layout.row()
        row.active = self.line_style is None

        def style_add_or_duplicate():
            # TODO copy cider_properties
            self.line_style = bpy.data.linestyles.new(f'{self.id_data.name} LineStyle')

        row = layout.row(align=True)
        row.template_ID(self, "line_style")
        if self.line_style:
            row.operator('wm.cider_callback', text='', icon='DUPLICATE').callback.set(style_add_or_duplicate, 'Duplicate')
            self.line_style.cider_parameters.draw_ui(layout)
        else:
            row.operator('wm.cider_callback', text='New', icon='ADD').callback.set(style_add_or_duplicate, 'New')

class CIDER_PT_MaterialSettings(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    bl_context = "material"
    bl_label = "Cider Settings"

    @classmethod
    def poll(cls, context):
        return is_cider_active() and context.object is not None

    def draw(self, context):
        layout = self.layout
        if context.material:
            context.material.cider.draw_ui(layout, context)

classes = (
    CiderMaterial,
    CIDER_PT_MaterialSettings,
)    

def register():
    for _class in classes: bpy.utils.register_class(_class)
    bpy.types.Material.cider = bpy.props.PointerProperty(type=CiderMaterial)

def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)
