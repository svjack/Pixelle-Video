"""
Template utility functions for size parsing and template management
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel, Field


def parse_template_size(template_path: str) -> Tuple[int, int]:
    """
    Parse video size from template path
    
    Args:
        template_path: Template path like "templates/1080x1920/default.html"
                      or "1080x1920/default.html"
    
    Returns:
        Tuple of (width, height) in pixels
    
    Raises:
        ValueError: If template path format is invalid
    
    Examples:
        >>> parse_template_size("templates/1080x1920/default.html")
        (1080, 1920)
        >>> parse_template_size("1920x1080/modern.html")
        (1920, 1080)
    """
    path = Path(template_path)
    
    # Get parent directory name (should be like "1080x1920")
    dir_name = path.parent.name
    
    # Special case: if parent is "templates", go up one more level
    if dir_name == "templates":
        # This shouldn't happen in new structure, but handle it
        raise ValueError(
            f"Invalid template path format: {template_path}. "
            f"Expected format: 'WIDTHxHEIGHT/template.html' or 'templates/WIDTHxHEIGHT/template.html'"
        )
    
    # Parse size from directory name
    if 'x' not in dir_name:
        raise ValueError(
            f"Invalid size format in path: {template_path}. "
            f"Directory name should be 'WIDTHxHEIGHT' (e.g., '1080x1920')"
        )
    
    try:
        width_str, height_str = dir_name.split('x')
        width = int(width_str)
        height = int(height_str)
        
        # Sanity check
        if width < 100 or height < 100 or width > 10000 or height > 10000:
            raise ValueError(f"Invalid size dimensions: {width}x{height}")
        
        return (width, height)
    except ValueError as e:
        raise ValueError(
            f"Failed to parse size from path: {template_path}. "
            f"Expected format: 'WIDTHxHEIGHT/template.html' (e.g., '1080x1920/default.html'). "
            f"Error: {e}"
        )


def list_available_sizes() -> List[str]:
    """
    List all available video sizes
    
    Returns:
        List of size strings like ["1080x1920", "1920x1080", "1080x1080"]
    
    Examples:
        >>> list_available_sizes()
        ['1080x1920', '1920x1080', '1080x1080']
    """
    templates_dir = Path("templates")
    
    if not templates_dir.exists():
        return []
    
    sizes = []
    for item in templates_dir.iterdir():
        if item.is_dir() and 'x' in item.name:
            # Validate it's a proper size format
            try:
                width, height = item.name.split('x')
                int(width)
                int(height)
                sizes.append(item.name)
            except (ValueError, AttributeError):
                # Skip invalid directories
                continue
    
    return sorted(sizes)


def list_templates_for_size(size: str) -> List[str]:
    """
    List all templates available for a given size
    
    Args:
        size: Size string like "1080x1920"
    
    Returns:
        List of template filenames (without path) like ["default.html", "modern.html"]
    
    Examples:
        >>> list_templates_for_size("1080x1920")
        ['cartoon.html', 'default.html', 'elegant.html', 'modern.html', ...]
    """
    size_dir = Path("templates") / size
    
    if not size_dir.exists() or not size_dir.is_dir():
        return []
    
    templates = []
    for item in size_dir.iterdir():
        if item.is_file() and item.suffix == '.html':
            templates.append(item.name)
    
    return sorted(templates)


def get_template_full_path(size: str, template_name: str) -> str:
    """
    Get full template path from size and template name
    
    Args:
        size: Size string like "1080x1920"
        template_name: Template filename like "default.html"
    
    Returns:
        Full path like "templates/1080x1920/default.html"
    
    Raises:
        FileNotFoundError: If template file doesn't exist
    
    Examples:
        >>> get_template_full_path("1080x1920", "default.html")
        'templates/1080x1920/default.html'
    """
    template_path = Path("templates") / size / template_name
    
    if not template_path.exists():
        available_templates = list_templates_for_size(size)
        raise FileNotFoundError(
            f"Template not found: {template_path}\n"
            f"Available templates for size {size}: {available_templates}"
        )
    
    return str(template_path)


class TemplateDisplayInfo(BaseModel):
    """Template display information for UI layer"""
    
    name: str = Field(..., description="Template name without extension")
    size: str = Field(..., description="Size string like '1080x1920'")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")
    orientation: Literal['portrait', 'landscape', 'square'] = Field(
        ..., 
        description="Video orientation"
    )
    is_standard: bool = Field(
        ..., 
        description="True only for standard sizes: 1080x1920, 1920x1080, 1080x1080"
    )


class TemplateInfo(BaseModel):
    """Complete template information with path and display info"""
    
    template_path: str = Field(..., description="Full template path like '1080x1920/default.html'")
    display_info: TemplateDisplayInfo = Field(..., description="Display information")


def format_template_display_info(template_name: str, size: str) -> TemplateDisplayInfo:
    """
    Format template display information for UI
    
    Returns structured data for UI layer to handle display and i18n.
    
    Args:
        template_name: Template filename like "default.html"
        size: Size string like "1080x1920"
    
    Returns:
        TemplateDisplayInfo object with name, size, dimensions, orientation, and standard flag
    
    Examples:
        >>> info = format_template_display_info("default.html", "1080x1920")
        >>> info.name
        'default'
        >>> info.is_standard
        True
        
        >>> info = format_template_display_info("custom.html", "1080x1921")
        >>> info.orientation
        'portrait'
        >>> info.is_standard
        False
    """
    # Keep full template name with .html extension
    name = template_name
    
    # Parse size
    width, height = map(int, size.split('x'))
    
    # Detect orientation
    if height > width:
        orientation = 'portrait'
    elif width > height:
        orientation = 'landscape'
    else:
        orientation = 'square'
    
    # Check if it's a standard size (only these three)
    is_standard = (width, height) in [(1080, 1920), (1920, 1080), (1080, 1080)]
    
    return TemplateDisplayInfo(
        name=name,
        size=size,
        width=width,
        height=height,
        orientation=orientation,
        is_standard=is_standard
    )


def get_all_templates_with_info() -> List[TemplateInfo]:
    """
    Get all templates with their display information
    
    Returns:
        List of TemplateInfo objects
    
    Example:
        >>> templates = get_all_templates_with_info()
        >>> for t in templates:
        ...     print(f"{t.display_info.name} - {t.display_info.orientation}")
        ...     print(f"  Path: {t.template_path}")
        ...     print(f"  Standard: {t.display_info.is_standard}")
    """
    result = []
    sizes = list_available_sizes()
    
    for size in sizes:
        templates = list_templates_for_size(size)
        for template in templates:
            display_info = format_template_display_info(template, size)
            full_path = f"{size}/{template}"
            result.append(TemplateInfo(
                template_path=full_path,
                display_info=display_info
            ))
    
    return result


def get_templates_grouped_by_size() -> dict:
    """
    Get templates grouped by size
    
    Returns:
        Dict with size as key, list of TemplateInfo as value
        Ordered by orientation priority: portrait > landscape > square
    
    Example:
        >>> grouped = get_templates_grouped_by_size()
        >>> for size, templates in grouped.items():
        ...     print(f"Size: {size}")
        ...     for t in templates:
        ...         print(f"  - {t.display_info.name}")
    """
    from collections import defaultdict
    
    templates = get_all_templates_with_info()
    grouped = defaultdict(list)
    
    for t in templates:
        grouped[t.display_info.size].append(t)
    
    # Sort groups by orientation priority: portrait > landscape > square
    orientation_priority = {'portrait': 0, 'landscape': 1, 'square': 2}
    
    sorted_grouped = {}
    for size in sorted(grouped.keys(), key=lambda s: (
        orientation_priority.get(grouped[s][0].display_info.orientation, 3),
        s
    )):
        sorted_grouped[size] = sorted(grouped[size], key=lambda t: t.display_info.name)
    
    return sorted_grouped


def resolve_template_path(template_input: Optional[str]) -> str:
    """
    Resolve template input to full path with validation
    
    Args:
        template_input: Can be:
            - None: Use default "1080x1920/default.html"
            - "template.html": Use default size + this template
            - "1080x1920/template.html": Full relative path
            - "templates/1080x1920/template.html": Absolute-ish path
    
    Returns:
        Resolved full path like "templates/1080x1920/default.html"
    
    Raises:
        FileNotFoundError: If template doesn't exist
    
    Examples:
        >>> resolve_template_path(None)
        'templates/1080x1920/default.html'
        >>> resolve_template_path("modern.html")
        'templates/1080x1920/modern.html'
        >>> resolve_template_path("1920x1080/default.html")
        'templates/1920x1080/default.html'
    """
    # Default case
    if template_input is None:
        template_input = "1080x1920/default.html"
    
    # If already starts with "templates/", use as-is
    if template_input.startswith("templates/"):
        template_path = Path(template_input)
    # If contains size directory (e.g., "1080x1920/default.html")
    elif '/' in template_input and 'x' in template_input.split('/')[0]:
        template_path = Path("templates") / template_input
    # Just template name (e.g., "default.html")
    else:
        # Use default size
        template_path = Path("templates") / "1080x1920" / template_input
    
    # Validate existence
    if not template_path.exists():
        available_sizes = list_available_sizes()
        raise FileNotFoundError(
            f"Template not found: {template_path}\n"
            f"Available sizes: {available_sizes}\n"
            f"Hint: Use format 'SIZExSIZE/template.html' (e.g., '1080x1920/default.html')"
        )
    
    return str(template_path)

