"""
批量遍历添加新人物示例

用法：
1. 修改 INPUT_PATTERN 指定要处理的JSON文件路径模式
2. 修改 OUTPUT_BASE_DIR 指定输出目录
3. 运行脚本
"""

import os
import glob
from table_pipline import run_pipeline_add_agent_variations

# ========== 配置区域 ==========

# 输入JSON文件路径模式（支持通配符）
INPUT_PATTERN = "./ownership/logs_rebuild/**/scene_data.json"

# 输出基础目录
OUTPUT_BASE_DIR = "./ownership/add_agent_batch_results"

# 是否打印详细信息（批量处理时建议设为False以减少输出）
PRINT_INFO = False

# ========== 处理逻辑 ==========

def main():
    # 查找所有匹配的场景JSON文件
    scene_files = glob.glob(INPUT_PATTERN, recursive=True)
    
    if not scene_files:
        print(f"[ERROR] 未找到匹配的JSON文件: {INPUT_PATTERN}")
        return
    
    print(f"\n{'='*80}")
    print(f"[INFO] 批量遍历添加新人物")
    print(f"{'='*80}")
    print(f"找到 {len(scene_files)} 个场景文件")
    print(f"输出目录: {OUTPUT_BASE_DIR}")
    print(f"{'='*80}\n")
    
    total_scenes = len(scene_files)
    success_scenes = 0
    failed_scenes = 0
    
    for idx, scene_file in enumerate(scene_files, 1):
        try:
            # 获取场景目录名称
            scene_dir_name = os.path.basename(os.path.dirname(scene_file))
            
            print(f"\n{'#'*80}")
            print(f"# 处理场景 {idx}/{total_scenes}: {scene_dir_name}")
            print(f"{'#'*80}")
            
            # 为每个场景创建独立的输出目录
            output_dir = os.path.join(OUTPUT_BASE_DIR, scene_dir_name)
            
            # 调用Pipeline函数
            run_pipeline_add_agent_variations(
                json_file_path=scene_file,
                base_output_dir=output_dir,
                print_info=PRINT_INFO
            )
            
            success_scenes += 1
            print(f"[SUCCESS] 场景 {idx}/{total_scenes} 处理完成: {scene_dir_name}")
        
        except Exception as e:
            failed_scenes += 1
            print(f"[ERROR] 场景 {idx}/{total_scenes} 处理失败: {scene_dir_name}")
            print(f"  错误信息: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # 打印最终统计
    print(f"\n{'='*80}")
    print(f"[DONE] 批量处理完成")
    print(f"{'='*80}")
    print(f"  总场景数: {total_scenes}")
    print(f"  成功: {success_scenes}")
    print(f"  失败: {failed_scenes}")
    print(f"  成功率: {success_scenes/total_scenes*100:.1f}%" if total_scenes > 0 else "  成功率: 0.0%")
    print(f"  结果目录: {OUTPUT_BASE_DIR}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
