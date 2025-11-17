# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Persistence Service

Handles task metadata and storyboard persistence to filesystem.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from pixelle_video.models.storyboard import Storyboard, StoryboardFrame, StoryboardConfig, ContentMetadata


class PersistenceService:
    """
    Task persistence service using filesystem (JSON)
    
    File structure:
        output/
        └── {task_id}/
            ├── metadata.json          # Task metadata (input, result, config)
            ├── storyboard.json        # Storyboard data (frames, prompts)
            ├── final.mp4
            └── frames/
                ├── 01_audio.mp3
                ├── 01_image.png
                └── ...
    
    Usage:
        persistence = PersistenceService()
        
        # Save metadata
        await persistence.save_task_metadata(task_id, metadata)
        
        # Save storyboard
        await persistence.save_storyboard(task_id, storyboard)
        
        # Load task
        metadata = await persistence.load_task_metadata(task_id)
        storyboard = await persistence.load_storyboard(task_id)
        
        # List all tasks
        tasks = await persistence.list_tasks(status="completed", limit=50)
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize persistence service
        
        Args:
            output_dir: Base output directory (default: "output")
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def get_task_dir(self, task_id: str) -> Path:
        """Get task directory path"""
        return self.output_dir / task_id
    
    def get_metadata_path(self, task_id: str) -> Path:
        """Get metadata.json path"""
        return self.get_task_dir(task_id) / "metadata.json"
    
    def get_storyboard_path(self, task_id: str) -> Path:
        """Get storyboard.json path"""
        return self.get_task_dir(task_id) / "storyboard.json"
    
    # ========================================================================
    # Metadata Operations
    # ========================================================================
    
    async def save_task_metadata(
        self,
        task_id: str,
        metadata: Dict[str, Any]
    ):
        """
        Save task metadata to filesystem
        
        Args:
            task_id: Task ID
            metadata: Metadata dict with structure:
                {
                    "task_id": str,
                    "created_at": str,
                    "completed_at": str (optional),
                    "status": str,
                    "input": dict,
                    "result": dict (optional),
                    "config": dict
                }
        """
        try:
            task_dir = self.get_task_dir(task_id)
            task_dir.mkdir(parents=True, exist_ok=True)
            
            metadata_path = self.get_metadata_path(task_id)
            
            # Ensure task_id is set
            metadata["task_id"] = task_id
            
            # Convert datetime objects to ISO format strings
            if "created_at" in metadata and isinstance(metadata["created_at"], datetime):
                metadata["created_at"] = metadata["created_at"].isoformat()
            if "completed_at" in metadata and isinstance(metadata["completed_at"], datetime):
                metadata["completed_at"] = metadata["completed_at"].isoformat()
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved task metadata: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to save task metadata {task_id}: {e}")
            raise
    
    async def load_task_metadata(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Load task metadata from filesystem
        
        Args:
            task_id: Task ID
            
        Returns:
            Metadata dict or None if not found
        """
        try:
            metadata_path = self.get_metadata_path(task_id)
            
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load task metadata {task_id}: {e}")
            return None
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """
        Update task status in metadata
        
        Args:
            task_id: Task ID
            status: New status (pending, running, completed, failed, cancelled)
            error: Error message (optional, for failed status)
        """
        try:
            metadata = await self.load_task_metadata(task_id)
            if not metadata:
                logger.warning(f"Cannot update status: task {task_id} not found")
                return
            
            metadata["status"] = status
            
            if status in ["completed", "failed", "cancelled"]:
                metadata["completed_at"] = datetime.now().isoformat()
            
            if error:
                metadata["error"] = error
            
            await self.save_task_metadata(task_id, metadata)
            
        except Exception as e:
            logger.error(f"Failed to update task status {task_id}: {e}")
    
    # ========================================================================
    # Storyboard Operations
    # ========================================================================
    
    async def save_storyboard(
        self,
        task_id: str,
        storyboard: Storyboard
    ):
        """
        Save storyboard to filesystem
        
        Args:
            task_id: Task ID
            storyboard: Storyboard instance
        """
        try:
            task_dir = self.get_task_dir(task_id)
            task_dir.mkdir(parents=True, exist_ok=True)
            
            storyboard_path = self.get_storyboard_path(task_id)
            
            # Convert storyboard to dict
            storyboard_dict = self._storyboard_to_dict(storyboard)
            
            with open(storyboard_path, "w", encoding="utf-8") as f:
                json.dump(storyboard_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved storyboard: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to save storyboard {task_id}: {e}")
            raise
    
    async def load_storyboard(self, task_id: str) -> Optional[Storyboard]:
        """
        Load storyboard from filesystem
        
        Args:
            task_id: Task ID
            
        Returns:
            Storyboard instance or None if not found
        """
        try:
            storyboard_path = self.get_storyboard_path(task_id)
            
            if not storyboard_path.exists():
                return None
            
            with open(storyboard_path, "r", encoding="utf-8") as f:
                storyboard_dict = json.load(f)
            
            # Convert dict to storyboard
            storyboard = self._dict_to_storyboard(storyboard_dict)
            
            return storyboard
            
        except Exception as e:
            logger.error(f"Failed to load storyboard {task_id}: {e}")
            return None
    
    # ========================================================================
    # Task Listing & Querying
    # ========================================================================
    
    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering
        
        Args:
            status: Filter by status (pending, running, completed, failed, cancelled)
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            
        Returns:
            List of metadata dicts, sorted by created_at descending
        """
        try:
            tasks = []
            
            # Scan all task directories
            for task_dir in self.output_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                
                metadata_path = task_dir / "metadata.json"
                if not metadata_path.exists():
                    continue
                
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    
                    # Filter by status
                    if status and metadata.get("status") != status:
                        continue
                    
                    tasks.append(metadata)
                    
                except Exception as e:
                    logger.warning(f"Failed to load metadata from {task_dir}: {e}")
                    continue
            
            # Sort by created_at descending
            tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
            
            # Apply pagination
            return tasks[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []
    
    async def task_exists(self, task_id: str) -> bool:
        """Check if task exists"""
        return self.get_task_dir(task_id).exists()
    
    async def delete_task(self, task_id: str):
        """
        Delete task directory and all files
        
        Args:
            task_id: Task ID
        """
        try:
            task_dir = self.get_task_dir(task_id)
            
            if task_dir.exists():
                import shutil
                shutil.rmtree(task_dir)
                logger.info(f"Deleted task: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise
    
    # ========================================================================
    # Serialization Helpers
    # ========================================================================
    
    def _storyboard_to_dict(self, storyboard: Storyboard) -> Dict[str, Any]:
        """Convert Storyboard to dict for JSON serialization"""
        return {
            "title": storyboard.title,
            "config": self._config_to_dict(storyboard.config),
            "frames": [self._frame_to_dict(frame) for frame in storyboard.frames],
            "content_metadata": self._content_metadata_to_dict(storyboard.content_metadata) if storyboard.content_metadata else None,
            "final_video_path": storyboard.final_video_path,
            "total_duration": storyboard.total_duration,
            "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
            "completed_at": storyboard.completed_at.isoformat() if storyboard.completed_at else None,
        }
    
    def _dict_to_storyboard(self, data: Dict[str, Any]) -> Storyboard:
        """Convert dict to Storyboard instance"""
        return Storyboard(
            title=data["title"],
            config=self._dict_to_config(data["config"]),
            frames=[self._dict_to_frame(frame_data) for frame_data in data["frames"]],
            content_metadata=self._dict_to_content_metadata(data["content_metadata"]) if data.get("content_metadata") else None,
            final_video_path=data.get("final_video_path"),
            total_duration=data.get("total_duration", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )
    
    def _config_to_dict(self, config: StoryboardConfig) -> Dict[str, Any]:
        """Convert StoryboardConfig to dict"""
        return {
            "task_id": config.task_id,
            "n_storyboard": config.n_storyboard,
            "min_narration_words": config.min_narration_words,
            "max_narration_words": config.max_narration_words,
            "min_image_prompt_words": config.min_image_prompt_words,
            "max_image_prompt_words": config.max_image_prompt_words,
            "video_fps": config.video_fps,
            "tts_inference_mode": config.tts_inference_mode,
            "voice_id": config.voice_id,
            "tts_workflow": config.tts_workflow,
            "tts_speed": config.tts_speed,
            "ref_audio": config.ref_audio,
            "image_width": config.image_width,
            "image_height": config.image_height,
            "image_workflow": config.image_workflow,
            "frame_template": config.frame_template,
            "template_params": config.template_params,
        }
    
    def _dict_to_config(self, data: Dict[str, Any]) -> StoryboardConfig:
        """Convert dict to StoryboardConfig"""
        return StoryboardConfig(
            task_id=data.get("task_id"),
            n_storyboard=data.get("n_storyboard", 5),
            min_narration_words=data.get("min_narration_words", 5),
            max_narration_words=data.get("max_narration_words", 20),
            min_image_prompt_words=data.get("min_image_prompt_words", 30),
            max_image_prompt_words=data.get("max_image_prompt_words", 60),
            video_fps=data.get("video_fps", 30),
            tts_inference_mode=data.get("tts_inference_mode", "local"),
            voice_id=data.get("voice_id"),
            tts_workflow=data.get("tts_workflow"),
            tts_speed=data.get("tts_speed"),
            ref_audio=data.get("ref_audio"),
            image_width=data.get("image_width", 1024),
            image_height=data.get("image_height", 1024),
            image_workflow=data.get("image_workflow"),
            frame_template=data.get("frame_template", "1080x1920/default.html"),
            template_params=data.get("template_params"),
        )
    
    def _frame_to_dict(self, frame: StoryboardFrame) -> Dict[str, Any]:
        """Convert StoryboardFrame to dict"""
        return {
            "index": frame.index,
            "narration": frame.narration,
            "image_prompt": frame.image_prompt,
            "audio_path": frame.audio_path,
            "media_type": frame.media_type,
            "image_path": frame.image_path,
            "video_path": frame.video_path,
            "composed_image_path": frame.composed_image_path,
            "video_segment_path": frame.video_segment_path,
            "duration": frame.duration,
            "created_at": frame.created_at.isoformat() if frame.created_at else None,
        }
    
    def _dict_to_frame(self, data: Dict[str, Any]) -> StoryboardFrame:
        """Convert dict to StoryboardFrame"""
        return StoryboardFrame(
            index=data["index"],
            narration=data["narration"],
            image_prompt=data["image_prompt"],
            audio_path=data.get("audio_path"),
            media_type=data.get("media_type"),
            image_path=data.get("image_path"),
            video_path=data.get("video_path"),
            composed_image_path=data.get("composed_image_path"),
            video_segment_path=data.get("video_segment_path"),
            duration=data.get("duration", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )
    
    def _content_metadata_to_dict(self, metadata: ContentMetadata) -> Dict[str, Any]:
        """Convert ContentMetadata to dict"""
        return {
            "title": metadata.title,
            "author": metadata.author,
            "subtitle": metadata.subtitle,
            "genre": metadata.genre,
            "summary": metadata.summary,
            "publication_year": metadata.publication_year,
            "cover_url": metadata.cover_url,
        }
    
    def _dict_to_content_metadata(self, data: Dict[str, Any]) -> ContentMetadata:
        """Convert dict to ContentMetadata"""
        return ContentMetadata(
            title=data["title"],
            author=data.get("author"),
            subtitle=data.get("subtitle"),
            genre=data.get("genre"),
            summary=data.get("summary"),
            publication_year=data.get("publication_year"),
            cover_url=data.get("cover_url"),
        )

