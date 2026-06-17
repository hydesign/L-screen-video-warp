# Copy the code below to Blender script window; select the plane that u want to export, and make sure the camera that is facing this plane is active
# u  will get the .json after doing this 


import bpy
import json
import os
from bpy_extras.object_utils import world_to_camera_view

def show_message(message, title="Export Result", icon="INFO"):
    def draw(self, context):
        for line in message.split("\n"):
            self.layout.label(text=line)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

try:
    # 如果在 Edit Mode，先切回 Object Mode，避免 mesh 数据没更新
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    scene = bpy.context.scene
    plane_obj = bpy.context.active_object

    if plane_obj is None:
        raise RuntimeError("没有选中对象。请先选中右边那个 flat warp plane。")

    if plane_obj.type != "MESH":
        raise RuntimeError(f"当前选中的不是 Mesh，而是 {plane_obj.type}。请选中右边那个平面。")

    output_cam = scene.camera

    if output_cam is None:
        raise RuntimeError("当前 Scene 没有 active camera。请先把拍右边平面的 camera 设为 active camera。")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = plane_obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    if not mesh.uv_layers.active:
        eval_obj.to_mesh_clear()
        raise RuntimeError("这个 plane 没有 active UV layer。请确认右边平面有 UV。")

    uv_layer = mesh.uv_layers.active.data
    mesh.calc_loop_triangles()

    tris = []

    for tri in mesh.loop_triangles:
        dst = []
        src = []

        for loop_index in tri.loops:
            loop = mesh.loops[loop_index]
            vertex = mesh.vertices[loop.vertex_index]

            world_pos = eval_obj.matrix_world @ vertex.co

            # destination: 当前平面在 output camera 画面中的 0-1 坐标
            cam_coord = world_to_camera_view(scene, output_cam, world_pos)

            dst.append([
                float(cam_coord.x),
                float(cam_coord.y)
            ])

            # source: 当前平面的 UV，之后会对应 normal video 的采样位置
            uv = uv_layer[loop_index].uv

            src.append([
                float(uv.x),
                float(uv.y)
            ])

        tris.append({
            "dst": dst,
            "src": src
        })

    eval_obj.to_mesh_clear()

    render_w = int(scene.render.resolution_x * scene.render.resolution_percentage / 100)
    render_h = int(scene.render.resolution_y * scene.render.resolution_percentage / 100)

    data = {
        "plane": plane_obj.name,
        "output_camera": output_cam.name,
        "render_resolution": [render_w, render_h],
        "triangles": tris
    }

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    export_path = os.path.join(desktop, "curved_screen_warp_map.json")

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    result = (
        "导出成功！\n"
        f"Plane: {plane_obj.name}\n"
        f"Camera: {output_cam.name}\n"
        f"Triangles: {len(tris)}\n"
        f"Resolution: {render_w} x {render_h}\n"
        f"Path: {export_path}"
    )

    print(result)
    show_message(result)

    # 在 Blender Text Editor 里也创建一个结果文本，方便你看
    if "EXPORT_RESULT" in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts["EXPORT_RESULT"])

    text_block = bpy.data.texts.new("EXPORT_RESULT")
    text_block.write(result)

except Exception as e:
    error_msg = f"导出失败：\n{str(e)}"
    print(error_msg)
    show_message(error_msg, title="Export Error", icon="ERROR")

    if "EXPORT_RESULT" in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts["EXPORT_RESULT"])

    text_block = bpy.data.texts.new("EXPORT_RESULT")
    text_block.write(error_msg)
