import bpy

class OT_CiderPrintError(bpy.types.Operator):
    bl_idname = "wm.cider_print_error"
    bl_label = "Print Cider Error"
    bl_description = "CIDER ERROR"
    bl_options = {'INTERNAL'}

    message : bpy.props.StringProperty(default="Cider Error", description='Error Message')

    @classmethod
    def description(cls, context, properties):
        return properties.message

    def execute(self, context):
        self.report({'ERROR'}, self.message)
        return {'FINISHED'}
    
    def modal(self, context, event):
        self.report({'ERROR'}, self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

# Always store paths in UNIX format so saved files work across OSs
def cider_path_set_transform(self, new_value, curr_value, is_set):
    return new_value.replace('\\','/')

def cider_path_get_transform(self, curr_value, is_set):
    return curr_value.replace('\\','/')

def is_cider_active():
    return bpy.context.scene.cider.enabled and bpy.context.scene.render.engine != 'MALT'

# Operator buttons are generated every time the UI is redrawn.
# The UI is redrawn for every frame the cursor hovers over it
# The operator button called is not the last one created (???)
# So _MAX_CALLBACKS should be at least (max drawn operator buttons) * (max ui redraws after the button was created)
_MAX_CALLBACKS = 1000
_CALLBACKS = [None] * _MAX_CALLBACKS
_LAST_HANDLE = 0

class CiderCallback(bpy.types.PropertyGroup):

    def set(self, callback, message=''):
        global _CALLBACKS, _LAST_HANDLE, _MAX_CALLBACKS
        _LAST_HANDLE += 1
        _LAST_HANDLE = _LAST_HANDLE % _MAX_CALLBACKS
        _CALLBACKS[_LAST_HANDLE] = callback
        self['_CIDER_CALLBACK_'] = _LAST_HANDLE
        self['_MESSAGE_'] = message
    
    def call(self, *args, **kwargs):
        global _CALLBACKS
        _CALLBACKS[self['_CIDER_CALLBACK_']](*args, **kwargs)

class OT_CiderCallback(bpy.types.Operator):
    bl_idname = "wm.cider_callback"
    bl_label = "Cider Callback Operator"
    bl_options = {'INTERNAL'}

    callback : bpy.props.PointerProperty(type=CiderCallback)

    @classmethod
    def description(self, context, properties):
        return properties.callback['_MESSAGE_']

    def execute(self, context):
        self.callback.call()
        return {'FINISHED'}

classes=[
    OT_CiderPrintError,
    CiderCallback,
    OT_CiderCallback,
]

def register():
    for _class in classes: bpy.utils.register_class(_class)

def unregister():
    global _CALLBACKS
    _CALLBACKS = [None] * _MAX_CALLBACKS
    for _class in reversed(classes): bpy.utils.unregister_class(_class)
