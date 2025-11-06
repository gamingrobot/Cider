import bpy
from . CiderUtils import is_cider_active

_PARAMS = None

class CiderMaterial(bpy.types.PropertyGroup):    

    def line_style_update(self, context):
        self.id_data.update_tag()

    line_style: bpy.props.PointerProperty(name="LineStyle", type=bpy.types.FreestyleLineStyle, update=line_style_update)

    def draw_ui(self, layout, context):
        layout.active = self.id_data.library is None #only local data can be edited
        row = layout.row()
        row.active = self.line_style is None
        row = layout.row(align=True)
        row.template_ID(self, "line_style", new="wm.cider_new_line_style")
        if self.line_style:
            self.line_style.cider_parameters.draw_ui(layout)

class OT_CiderNewLineStyle(bpy.types.Operator):
    bl_idname = "wm.cider_new_line_style"
    bl_label = "Cider New LineStyle Operator"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        if context.material:
            if context.material.cider.line_style:
                line_style = bpy.data.linestyles.new(context.material.cider.line_style.name)
                global _PARAMS
                line_style.cider_parameters.setup(_PARAMS, replace_parameters=False, copy_from=context.material.cider.line_style.cider_parameters)
                context.material.cider.line_style = line_style
            else:
                context.material.cider.line_style = bpy.data.linestyles.new(f'{context.material.id_data.name} LineStyle') 
        return {'FINISHED'}

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

def update_params(params):
    global _PARAMS
    _PARAMS = params

classes = (
    CiderMaterial,
    OT_CiderNewLineStyle,
    CIDER_PT_MaterialSettings,
)    

def register():
    for _class in classes: bpy.utils.register_class(_class)
    bpy.types.Material.cider = bpy.props.PointerProperty(type=CiderMaterial)

def unregister():
    for _class in reversed(classes): bpy.utils.unregister_class(_class)
