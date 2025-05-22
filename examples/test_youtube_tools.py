import os
import json
from dotenv import load_dotenv

# Assuming youtube.py is in the same directory or accessible in PYTHONPATH
from youtube import YouTubeVideoSearchTool, YouTubeVideoTranscriptTool

def run_tests():
    """运行 YouTubeVideoSearchTool 和 YouTubeVideoTranscriptTool 的测试."""
    print("--- 开始 YouTube 工具测试 ---")

    # 1. 加载环境变量 (特别是 RAPIDAPI_KEY)
    load_dotenv()
    print("环境变量已加载。\n")

    video_ids_from_search = [] # 用于存储从搜索结果中提取的视频ID

    # 2. 测试 YouTubeVideoSearchTool
    print("--- 测试 YouTubeVideoSearchTool ---")
    try:
        search_tool = YouTubeVideoSearchTool()
        search_query = "最新AI进展" # 使用中文查询示例
        print(f"搜索工具：已实例化。查询: '{search_query}'")
        
        search_output_json = search_tool.forward(query=search_query)
        print(f"搜索工具：原始输出:\n{search_output_json}")

        try:
            search_results = json.loads(search_output_json)
            print(f"搜索工具：成功解析JSON输出。结果数量: {len(search_results) if isinstance(search_results, list) else 'N/A'}")
            
            # 检查搜索结果是否为列表且包含实际视频数据 (通过检查'url'键是否存在于第一项)
            if isinstance(search_results, list) and search_results and \
               isinstance(search_results[0], dict) and 'url' in search_results[0]:
                
                print(f"搜索工具：第一个结果标题: {search_results[0].get('title')}")
                print("\n将从搜索结果中提取视频ID用于转录测试。")
                count = 0
                for video_item in search_results:
                    if count >= 5: # 最多提取5个
                        break
                    if isinstance(video_item, dict):
                        url = video_item.get('url')
                        if url and isinstance(url, str) and 'watch?v=' in url:
                            try:
                                video_id_part = url.split('watch?v=')[1]
                                video_id = video_id_part.split('&')[0].strip()
                                if video_id: # 确保 video_id 不为空
                                    video_ids_from_search.append(video_id)
                                    count += 1
                                else:
                                    print(f"警告：从URL '{url}' 提取到空的视频ID。")
                            except IndexError:
                                print(f"警告：无法从URL '{url}' 解析视频ID。")
                        # else: # 可以在此添加对缺少URL的项目的警告，但通常搜索结果应包含URL
                        #     print(f"警告：视频项目 '{video_item.get('title', '未知标题')}' 缺少有效URL。")
                
                if video_ids_from_search:
                    print(f"已成功从搜索结果中提取 {len(video_ids_from_search)} 个视频ID: {video_ids_from_search}")
                else:
                    print("搜索成功，但未能从返回的结果中提取任何有效的视频ID。")
            
            elif isinstance(search_results, list) and search_results and \
                 isinstance(search_results[0], dict) and ('error' in search_results[0] or 'message' in search_results[0]):
                 print(f"搜索工具：API返回消息/错误: {search_results[0]}")
            else:
                print("搜索工具：无有效视频结果或返回格式非预期。")
        except json.JSONDecodeError as e:
            print(f"搜索工具：解析JSON输出失败。错误: {e}")
        except Exception as e:
            print(f"搜索工具：处理搜索结果时出错: {e}")

    except Exception as e:
        print(f"搜索工具：严重错误 - 实例化或运行时失败: {e}")
    print("--- YouTubeVideoSearchTool 测试完成 ---\n")

    # 3. 测试 YouTubeVideoTranscriptTool
    print("--- 测试 YouTubeVideoTranscriptTool ---")
    
    ids_to_use_for_transcription = []
    source_of_ids_message = ""

    if video_ids_from_search:
        ids_to_use_for_transcription = video_ids_from_search
        source_of_ids_message = f"将使用从上方搜索结果中提取的 {len(ids_to_use_for_transcription)} 个视频ID进行测试: {ids_to_use_for_transcription}"
    else:
        print("由于未能从搜索结果中获取有效的视频ID，将使用预定义的备用ID列表进行转录工具测试。")
        ids_to_use_for_transcription = ['dQw4w9WgXcQ', 'jNQXAC9IVRw', 'INVALIDID789', '', 'G3JjSQI4FE8'] # 备用列表，包含有效、无效和特殊ID
        source_of_ids_message = f"使用备用列表测试 {len(ids_to_use_for_transcription)} 个视频ID: {ids_to_use_for_transcription}"

    if not ids_to_use_for_transcription:
        print("转录工具：没有可用的视频ID进行测试（搜索和备用均失败），跳过此测试部分。")
    else:
        try:
            transcript_tool = YouTubeVideoTranscriptTool()
            print(f"转录工具：已实例化。{source_of_ids_message}")

            transcript_output_json = transcript_tool.forward(video_ids=ids_to_use_for_transcription)
            print(f"转录工具：原始输出:\n{transcript_output_json}")

            try:
                transcript_results_list = json.loads(transcript_output_json)
                print(f"转录工具：成功解析JSON输出。结果对象数量: {len(transcript_results_list) if isinstance(transcript_results_list, list) else 'N/A'}")
                
                if not isinstance(transcript_results_list, list):
                    print(f"转录工具：期望获得列表作为顶层JSON结构，但得到: {type(transcript_results_list)}")
                else:
                    for i, result_item in enumerate(transcript_results_list):
                        if not isinstance(result_item, dict):
                            print(f"  结果项 {i} (应为字典) 格式不正确: {result_item}")
                            continue
                        print(f"  视频ID '{result_item.get('video_id', 'N/A')}' 的结果:")
                        transcript_data = result_item.get('transcript_result')
                        if isinstance(transcript_data, list) and transcript_data: # 成功获取转录片段列表
                            print(f"    类型: 成功, 片段数量: {len(transcript_data)}")
                            print(f"    第一个片段文本 (如有): {transcript_data[0].get('text', 'N/A')[:50]}...")
                        elif isinstance(transcript_data, dict) and "error" in transcript_data: # 转录此视频时发生错误
                            print(f"    类型: 错误, 消息: {transcript_data['error']}")
                        else: # 其他未知情况
                            print(f"    类型: 未知/空 - {transcript_data}")
            except json.JSONDecodeError as e:
                print(f"转录工具：解析JSON输出失败。错误: {e}")
            except Exception as e:
                print(f"转录工具：处理转录结果时出错: {e}")

        except Exception as e:
            print(f"转录工具：严重错误 - 实例化或运行时失败: {e}")
    print("--- YouTubeVideoTranscriptTool 测试完成 ---\n")

    print("--- YouTube 工具测试结束 ---")

if __name__ == "__main__":
    run_tests() 