import os
import time
from pathlib import Path
from typing import Any

import streamlit as st
from loguru import logger
import httpx
from web.i18n import tr, get_language
from web.pipelines.base import PipelineUI, register_pipeline_ui
from web.components.content_input import render_bgm_section, render_version_info
from web.utils.async_helpers import run_async
from pixelle_video.config import config_manager
from pixelle_video.utils.os_util import create_task_output_dir

class AudioVisualPipelineUI(PipelineUI):
    """
    UI for the Audio-visual synchronization Video Generation Pipeline.
    Generates videos from user-provided assets (images&text).
    """
    name = "voice_synchronization"
    icon = "🎥"
    
    @property
    def display_name(self):
        return tr("pipeline.audio-visual.name")
    
    @property
    def description(self):
        return tr("pipeline.audio-visual.description")

    def render(self, pixelle_video: Any):
        # Three-column layout
        left_col,right_col = st.columns([1, 1])

        # ====================================================================
        # Middle Column: Asset Upload
        # ====================================================================
        with left_col:
            asset_params = self.render_audio_visual_input()
            render_version_info()

        with right_col:
            video_params = {
                **asset_params
            }

            self._render_output_preview(pixelle_video, video_params)

    def render_audio_visual_input(self) -> dict:

        # File uploader for multiple files
        uploaded_files = st.file_uploader(
            tr("audio_visual.assets.upload"),
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help=tr("audio_visual.assets.upload_help"),
            key="material_files"
        )

        # Save uploaded files to temp directory with unique session ID
        audio_asset_paths = []
        if uploaded_files:
            import uuid
            session_id = str(uuid.uuid4()).replace('-', '')[:12]
            temp_dir = Path(f"temp/assets_{session_id}")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            for uploaded_file in uploaded_files:
                file_path = temp_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                audio_asset_paths.append(str(file_path.absolute()))
            
            st.success(tr("audio_visual.assets.character_sucess"))
            
            # Preview uploaded assets
            with st.expander(tr("audio_visual.assets.preview"), expanded=True):
                # Show in a grid (3 columns)
                cols = st.columns(3)
                for i, (file, path) in enumerate(zip(uploaded_files, audio_asset_paths)):
                    with cols[i % 3]:
                        # Check if image
                        ext = Path(path).suffix.lower()
                        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                            st.image(file, caption=file.name, use_container_width=True)
        else:
            st.info(tr("audio_visual.assets.character_empty_hint"))
        
        prompt_text = st.text_area(
                    tr("audio_visual.input_text"),
                    placeholder=tr("audio_visual.input.topic_placeholder"),
                    height=200,
                    help=tr("input.text_help_audio"),
                    key="audio_box"
                    )
        
        return {
                    "audio_assets": audio_asset_paths,
                    "prompt_text": prompt_text,
                    }

    def _render_output_preview(self, pixelle_video: Any, video_params: dict):
        """Render output preview section"""
        with st.container(border=True):
            st.markdown(f"**{tr('section.video_generation')}**")
            
            # Check configuration
            if not config_manager.validate():
                st.warning(tr("settings.not_configured"))

            audio_assets = video_params.get("audio_assets", [])
            prompt_text = video_params.get("prompt_text", "")

            logger.info(f"video_params: {video_params}")
            
            if not audio_assets:
                st.info(tr("audio_visual.assets.image_warning"))
                st.button(
                    tr("btn.generate"),
                    type="primary",
                    use_container_width=True,
                    disabled=True,
                    key="audio_visual_generate_disabled"
                )
                return

            if not prompt_text:
                st.info(tr("audio_visual.assets.prompt_warning"))
                st.button(
                    tr("btn.generate"),
                    type="primary",
                    use_container_width=True,
                    disabled=True,
                    key="audio_visual_generate"
                )
                return
            
            # Generate button
            if st.button(tr("btn.generate"), type="primary", use_container_width=True, key="digital_human_generate"):
                # Validate
                if not config_manager.validate():
                    st.error(tr("settings.not_configured"))
                    st.stop()
                
                 # Show progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                start_time = time.time()
                
                try:
                    # Define async generation function
                    async def generate_audio_visual_video():
                        task_dir, task_id = create_task_output_dir()
                        kit = await pixelle_video._get_or_create_comfykit()

                        import json
                        from pathlib import Path

                        status_text.text(tr("progress.generation"))
                        progress_bar.progress(65)
                        image_path = audio_assets[0]
                        prompt = prompt_text

                        workflow_path = Path("workflows/runninghub/audio_visual.json")
                        if not workflow_path.exists():
                            raise Exception(f"The workflow file does not exist: {workflow_path}")
                        with open(workflow_path, 'r', encoding='utf-8') as f:
                            workflow_config = json.load(f)
                        workflow_params = {
                            "image": image_path,
                            "prompt": prompt
                        }
                        if workflow_config.get("source") == "runninghub" and "workflow_id" in workflow_config:
                            workflow_input = workflow_config["workflow_id"]
                        else:
                            workflow_input = str(workflow_path)
                        video_result = await kit.execute(workflow_input, workflow_params)

                        generated_video_url = None
                        if hasattr(video_result, 'videos') and video_result.videos:
                            generated_video_url = video_result.videos[0]
                        elif hasattr(video_result, 'outputs') and video_result.outputs:
                            for node_id, node_output in video_result.outputs.items():
                                if isinstance(node_output, dict) and 'videos' in node_output:
                                    videos = node_output['videos']
                                    if videos and len(videos) > 0:
                                        generated_video_url = videos[0]
                                        break
                        if not generated_video_url:
                            raise Exception("The workflow did not return a video. Please check the workflow configuration.")
                                    
                        final_video_path = os.path.join(task_dir, "final.mp4")
                        timeout = httpx.Timeout(300.0)
                        async with httpx.AsyncClient(timeout=timeout) as client:
                            response = await client.get(generated_video_url)
                            response.raise_for_status()
                            with open(final_video_path, 'wb') as f:
                                f.write(response.content)
                        progress_bar.progress(100)
                        status_text.text(tr("status.success"))
                        return final_video_path
                    
                    # Execute async generation
                    final_video_path = run_async(generate_audio_visual_video())
                    
                    total_time = time.time() - start_time
                    progress_bar.progress(100)
                    status_text.text(tr("status.success"))
                    
                    # Display result
                    st.success(tr("status.video_generated", path=final_video_path))
                    
                    st.markdown("---")
                    
                    # Video info
                    if os.path.exists(final_video_path):
                        file_size_mb = os.path.getsize(final_video_path) / (1024 * 1024)
                        
                        info_text = (
                            f"⏱️ {tr('info.generation_time')} {total_time:.1f}s   "
                            f"📦 {file_size_mb:.2f}MB"
                        )
                        st.caption(info_text)
                        
                        st.markdown("---")
                        
                        # Video preview
                        st.video(final_video_path)
                        
                        # Download button
                        with open(final_video_path, "rb") as video_file:
                            video_bytes = video_file.read()
                            video_filename = os.path.basename(final_video_path)
                            st.download_button(
                                label="⬇️ 下载视频" if get_language() == "zh_CN" else "⬇️ Download Video",
                                data=video_bytes,
                                file_name=video_filename,
                                mime="video/mp4",
                                use_container_width=True
                            )
                    else:
                        st.error(tr("status.video_not_found", path=final_video_path))
                
                except Exception as e:
                    status_text.text("")
                    progress_bar.empty()
                    st.error(tr("status.error", error=str(e)))
                    logger.exception(e)
                    st.stop()

register_pipeline_ui(AudioVisualPipelineUI)
