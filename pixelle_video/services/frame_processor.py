"""
Frame processor - Process single frame through complete pipeline

Orchestrates: TTS → Image Generation → Frame Composition → Video Segment
"""

from typing import Callable, Optional

import httpx
from loguru import logger

from pixelle_video.models.progress import ProgressEvent
from pixelle_video.models.storyboard import Storyboard, StoryboardFrame, StoryboardConfig


class FrameProcessor:
    """Frame processor"""
    
    def __init__(self, pixelle_video_core):
        """
        Initialize
        
        Args:
            pixelle_video_core: PixelleVideoCore instance
        """
        self.core = pixelle_video_core
    
    async def __call__(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig,
        total_frames: int = 1,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None
    ) -> StoryboardFrame:
        """
        Process single frame through complete pipeline
        
        Steps:
        1. Generate audio (TTS)
        2. Generate image (ComfyKit)
        3. Compose frame (add subtitle)
        4. Create video segment (image + audio)
        
        Args:
            frame: Storyboard frame to process
            storyboard: Storyboard instance
            config: Storyboard configuration
            total_frames: Total number of frames in storyboard
            progress_callback: Optional callback for progress updates (receives ProgressEvent)
            
        Returns:
            Processed frame with all paths filled
        """
        logger.info(f"Processing frame {frame.index}...")
        
        frame_num = frame.index + 1
        
        try:
            # Step 1: Generate audio (TTS)
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.0,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=1,
                    action="audio"
                ))
            await self._step_generate_audio(frame, config)
            
            # Step 2: Generate image (ComfyKit)
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.25,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=2,
                    action="image"
                ))
            await self._step_generate_image(frame, config)
            
            # Step 3: Compose frame (add subtitle)
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.50,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=3,
                    action="compose"
                ))
            await self._step_compose_frame(frame, storyboard, config)
            
            # Step 4: Create video segment
            if progress_callback:
                progress_callback(ProgressEvent(
                    event_type="frame_step",
                    progress=0.75,
                    frame_current=frame_num,
                    frame_total=total_frames,
                    step=4,
                    action="video"
                ))
            await self._step_create_video_segment(frame, config)
            
            logger.info(f"✅ Frame {frame.index} completed")
            return frame
            
        except Exception as e:
            logger.error(f"❌ Failed to process frame {frame.index}: {e}")
            raise
    
    async def _step_generate_audio(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """Step 1: Generate audio using TTS"""
        logger.debug(f"  1/4: Generating audio for frame {frame.index}...")
        
        # Generate output path using task_id
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "audio")
        
        # Call TTS with specific output path and workflow
        tts_params = {
            "text": frame.narration,
            "workflow": config.tts_workflow,
            "voice": config.voice_id,
            "speed": config.tts_speed,
            "output_path": output_path,
        }
        
        # Add ref_audio if provided
        if config.ref_audio:
            tts_params["ref_audio"] = config.ref_audio
        
        audio_path = await self.core.tts(**tts_params)
        
        frame.audio_path = audio_path
        
        # Get audio duration
        frame.duration = await self._get_audio_duration(audio_path)
        
        logger.debug(f"  ✓ Audio generated: {audio_path} ({frame.duration:.2f}s)")
    
    async def _step_generate_image(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """Step 2: Generate image using ComfyKit"""
        logger.debug(f"  2/4: Generating image for frame {frame.index}...")
        
        # Call Image generation (with optional preset)
        image_url = await self.core.image(
            prompt=frame.image_prompt,
            workflow=config.image_workflow,  # Pass workflow from config (None = use default)
            width=config.image_width,
            height=config.image_height
        )
        
        # Download image to local (pass task_id)
        local_path = await self._download_image(image_url, frame.index, config.task_id)
        frame.image_path = local_path
        
        logger.debug(f"  ✓ Image generated: {local_path}")
    
    async def _step_compose_frame(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig
    ):
        """Step 3: Compose frame with subtitle using HTML template"""
        logger.debug(f"  3/4: Composing frame {frame.index}...")
        
        # Generate output path using task_id
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "composed")
        
        # Use HTML template to compose frame
        composed_path = await self._compose_frame_html(frame, storyboard, config, output_path)
        
        frame.composed_image_path = composed_path
        
        logger.debug(f"  ✓ Frame composed: {composed_path}")
    
    async def _compose_frame_html(
        self,
        frame: StoryboardFrame,
        storyboard: 'Storyboard',
        config: StoryboardConfig,
        output_path: str
    ) -> str:
        """Compose frame using HTML template"""
        from pixelle_video.services.frame_html import HTMLFrameGenerator
        from pixelle_video.utils.template_util import resolve_template_path
        
        # Resolve template path (handles various input formats)
        template_path = resolve_template_path(config.frame_template)
        
        # Get content metadata from storyboard
        content_metadata = storyboard.content_metadata if storyboard else None
        
        # Build ext data
        ext = {}
        if content_metadata:
            ext["content_title"] = content_metadata.title or ""
            ext["content_author"] = content_metadata.author or ""
            ext["content_subtitle"] = content_metadata.subtitle or ""
            ext["content_genre"] = content_metadata.genre or ""
        
        # Generate frame using HTML (size is auto-parsed from template path)
        generator = HTMLFrameGenerator(template_path)
        composed_path = await generator.generate_frame(
            title=storyboard.title,
            text=frame.narration,
            image=frame.image_path,
            ext=ext,
            output_path=output_path
        )
        
        return composed_path
    
    async def _step_create_video_segment(
        self,
        frame: StoryboardFrame,
        config: StoryboardConfig
    ):
        """Step 4: Create video segment from image + audio"""
        logger.debug(f"  4/4: Creating video segment for frame {frame.index}...")
        
        # Generate output path using task_id
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(config.task_id, frame.index, "segment")
        
        # Call video compositor to create video from image + audio
        from pixelle_video.services.video import VideoService
        video_service = VideoService()
        
        segment_path = video_service.create_video_from_image(
            image=frame.composed_image_path,
            audio=frame.audio_path,
            output=output_path,
            fps=config.video_fps
        )
        
        frame.video_segment_path = segment_path
        
        logger.debug(f"  ✓ Video segment created: {segment_path}")
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds"""
        try:
            # Try using ffmpeg-python
            import ffmpeg
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}, using estimate")
            # Fallback: estimate based on file size (very rough)
            import os
            file_size = os.path.getsize(audio_path)
            # Assume ~16kbps for MP3, so 2KB per second
            estimated_duration = file_size / 2000
            return max(1.0, estimated_duration)  # At least 1 second
    
    async def _download_image(self, url: str, frame_index: int, task_id: str) -> str:
        """Download image from URL to local file"""
        from pixelle_video.utils.os_util import get_task_frame_path
        output_path = get_task_frame_path(task_id, frame_index, "image")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
        
        return output_path

