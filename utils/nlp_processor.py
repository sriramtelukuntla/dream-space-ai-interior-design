import re
import os
from dotenv import load_dotenv

load_dotenv()

class PromptAnalyzer:
    """
    UPGRADED Prompt Analyzer with Enhanced Capabilities
    
    Improvements:
    - Handles much longer prompts (no token limit)
    - Better pattern matching for complex descriptions
    - Extracts more details (materials, textures, ambiance)
    - Smarter furniture detection
    - Better color extraction with shades
    - Lighting and mood detection
    """
    
    def __init__(self):
        # Extended room types
        self.room_furniture = {
            'bedroom': ['bed', 'king bed', 'queen bed', 'nightstand', 'bedside table', 'wardrobe', 
                       'closet', 'dresser', 'chest of drawers', 'study table', 'desk', 'chair', 
                       'armchair', 'curtains', 'drapes', 'lamp', 'floor lamp', 'table lamp',
                       'mirror', 'rug', 'carpet', 'bench'],
            
            'kitchen': ['cabinets', 'upper cabinets', 'lower cabinets', 'countertops', 'counter',
                       'island', 'kitchen island', 'stove', 'range', 'oven', 'refrigerator', 'fridge',
                       'sink', 'dishwasher', 'dining table', 'breakfast table', 'chairs', 'bar stools',
                       'shelves', 'open shelving', 'pantry', 'backsplash', 'range hood'],
            
            'bathroom': ['sink', 'vanity', 'double vanity', 'toilet', 'shower', 'walk-in shower',
                        'bathtub', 'freestanding tub', 'soaking tub', 'mirror', 'medicine cabinet',
                        'cabinet', 'storage', 'towel rack', 'towel bar', 'shower door', 'tiles'],
            
            'living room': ['sofa', 'couch', 'sectional', 'loveseat', 'coffee table', 'side table',
                           'end table', 'tv stand', 'entertainment center', 'bookshelf', 'bookcase',
                           'lamp', 'floor lamp', 'table lamp', 'curtains', 'drapes', 'rug', 'carpet',
                           'ottoman', 'accent chair', 'armchair', 'console table', 'fireplace'],
            
            'office': ['desk', 'work desk', 'computer desk', 'office chair', 'ergonomic chair',
                      'bookshelf', 'bookcase', 'filing cabinet', 'storage', 'computer', 'monitor',
                      'lamp', 'desk lamp', 'whiteboard', 'bulletin board', 'printer stand'],
            
            'dining room': ['dining table', 'table', 'dining chairs', 'chairs', 'buffet', 'sideboard',
                           'china cabinet', 'chandelier', 'pendant lights', 'rug', 'centerpiece'],
            
            'lab': ['lab tables', 'work benches', 'stools', 'lab stools', 'cabinets', 'storage cabinets',
                   'sink', 'fume hood', 'equipment racks', 'shelving', 'safety equipment'],
            
            'classroom': ['desks', 'student desks', 'chairs', 'student chairs', 'whiteboard', 'blackboard',
                         'projector', 'screen', 'teacher desk', 'podium', 'bulletin board', 'storage'],
            
            'auditorium': ['seats', 'auditorium seating', 'rows of seats', 'stage', 'podium', 'lectern',
                          'lights', 'stage lights', 'sound system', 'speakers', 'projector', 'screen'],
            
            'hall': ['seating area', 'bench', 'console table', 'entry table', 'mirror', 'coat rack',
                    'coat hooks', 'shoe storage', 'decorations', 'artwork', 'runner rug']
        }
        
        # Extended and nuanced color palette
        self.color_palette = {
            'warm': ['red', 'crimson', 'burgundy', 'orange', 'burnt orange', 'yellow', 'golden',
                    'beige', 'tan', 'brown', 'chocolate', 'gold', 'amber', 'coral', 'peach',
                    'terracotta', 'rust', 'copper'],
            
            'cool': ['blue', 'navy', 'royal blue', 'sky blue', 'light blue', 'teal', 'turquoise',
                    'cyan', 'aqua', 'green', 'forest green', 'sage', 'mint', 'emerald',
                    'purple', 'lavender', 'violet', 'indigo', 'plum', 'mauve'],
            
            'neutral': ['white', 'off-white', 'ivory', 'cream', 'beige', 'gray', 'grey', 'charcoal',
                       'black', 'taupe', 'khaki', 'silver', 'pewter', 'stone', 'sand'],
            
            'earth': ['brown', 'tan', 'olive', 'terracotta', 'sage', 'khaki', 'moss', 'clay',
                     'sienna', 'umber', 'ochre']
        }
        
        self.all_colors = list(set([color for colors in self.color_palette.values() for color in colors]))
        
        # Extended styles
        self.styles = [
            'modern', 'contemporary', 'minimalist', 'minimal', 'traditional', 'classic',
            'rustic', 'industrial', 'scandinavian', 'nordic', 'bohemian', 'boho',
            'coastal', 'nautical', 'mid-century', 'mid-century modern', 'vintage',
            'retro', 'farmhouse', 'country', 'art deco', 'zen', 'japanese', 'eclectic',
            'transitional', 'victorian', 'french country', 'shabby chic', 'mediterranean',
            'tropical', 'glamorous', 'luxury', 'elegant'
        ]
        
        # NEW: Materials and textures
        self.materials = [
            'wood', 'wooden', 'oak', 'walnut', 'pine', 'mahogany', 'bamboo',
            'metal', 'steel', 'iron', 'brass', 'copper', 'aluminum',
            'glass', 'marble', 'granite', 'stone', 'concrete',
            'leather', 'fabric', 'velvet', 'linen', 'cotton', 'silk',
            'tile', 'ceramic', 'porcelain', 'laminate', 'vinyl'
        ]
        
        # NEW: Lighting types
        self.lighting_types = [
            'natural light', 'natural lighting', 'sunlight', 'daylight',
            'ambient lighting', 'task lighting', 'accent lighting',
            'warm lighting', 'cool lighting', 'bright', 'dim', 'soft lighting',
            'chandelier', 'pendant lights', 'recessed lighting', 'track lighting',
            'floor lamps', 'table lamps', 'wall sconces', 'LED strips'
        ]
        
        # NEW: Mood/ambiance keywords
        self.mood_keywords = [
            'cozy', 'comfortable', 'inviting', 'warm', 'welcoming',
            'spacious', 'airy', 'open', 'bright', 'light',
            'elegant', 'sophisticated', 'luxurious', 'opulent',
            'calm', 'peaceful', 'serene', 'tranquil', 'relaxing',
            'energetic', 'vibrant', 'bold', 'dramatic',
            'minimalist', 'clean', 'simple', 'uncluttered'
        ]
    
    def analyze_prompt(self, user_prompt, room_type=None):
        """
        UPGRADED: Analyze prompts of any length with enhanced extraction
        
        Now extracts:
        - Room type
        - Dimensions
        - Colors (overall + directional)
        - Furniture
        - Style
        - Materials
        - Lighting
        - Mood/Ambiance
        - Special requirements
        """
        try:
            # Handle very long prompts by splitting into sentences
            prompt_lower = user_prompt.lower()
            
            parsed_data = {
                'room_type': room_type,
                'dimensions': {},
                'colors': {},
                'furniture': [],
                'style': 'modern',
                'materials': [],
                'lighting': [],
                'mood': [],
                'special_requirements': []
            }
            
            # Extract all components
            if not parsed_data['room_type']:
                parsed_data['room_type'] = self._extract_room_type(prompt_lower)
            
            parsed_data['dimensions'] = self._extract_dimensions(user_prompt)
            parsed_data['colors'] = self._extract_colors(user_prompt)
            parsed_data['furniture'] = self._extract_furniture(user_prompt, parsed_data['room_type'])
            parsed_data['style'] = self._extract_style(user_prompt)
            parsed_data['materials'] = self._extract_materials(user_prompt)
            parsed_data['lighting'] = self._extract_lighting(user_prompt)
            parsed_data['mood'] = self._extract_mood(user_prompt)
            parsed_data['special_requirements'] = self._extract_special_requirements(user_prompt)
            
            return parsed_data
            
        except Exception as e:
            print(f"Error in analyze_prompt: {e}")
            return self._get_default_structure(room_type)
    
    def _get_default_structure(self, room_type=None):
        """Return safe default structure"""
        return {
            'room_type': room_type or 'room',
            'dimensions': {},
            'colors': {'overall': []},
            'furniture': [],
            'style': 'modern',
            'materials': [],
            'lighting': [],
            'mood': [],
            'special_requirements': []
        }
    
    def _extract_room_type(self, text_lower):
        """Extract room type with priority (specific before general)"""
        # Check specific rooms first
        specific_rooms = ['dining room', 'living room', 'master bedroom', 'guest bedroom']
        for room in specific_rooms:
            if room in text_lower:
                return room
        
        # Then check general rooms
        for room in self.room_furniture.keys():
            if room in text_lower:
                return room
        
        return 'room'
    
    def _extract_dimensions(self, text):
        """ENHANCED: Extract dimensions with multiple patterns"""
        dimensions = {}
        text_lower = text.lower()
        
        try:
            # Pattern 1: "12x10 feet" or "12 x 10 ft" or "12 by 10 feet"
            patterns = [
                r'(\d+\.?\d*)\s*(?:x|×|by)\s*(\d+\.?\d*)\s*(feet|ft|foot|meters|m|metre|metres)\b',
                r'(\d+\.?\d*)\s*(feet|ft|foot|meters|m)\s*(?:x|×|by)\s*(\d+\.?\d*)\s*(feet|ft|foot|meters|m)\b',
                r'(\d+\.?\d*)\s*(?:x|×|by)\s*(\d+\.?\d*)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    groups = match.groups()
                    dimensions['width'] = float(groups[0])
                    
                    # Find the length (could be in different positions)
                    for i, group in enumerate(groups[1:], 1):
                        try:
                            length = float(group)
                            dimensions['length'] = length
                            break
                        except (ValueError, TypeError):
                            continue
                    
                    # Extract unit
                    unit_found = False
                    for group in groups:
                        if group and group in ['feet', 'ft', 'foot', 'meters', 'm', 'metre', 'metres']:
                            dimensions['unit'] = 'feet' if group in ['feet', 'ft', 'foot'] else 'meters'
                            unit_found = True
                            break
                    
                    if not unit_found:
                        dimensions['unit'] = 'feet'
                    
                    break
            
            # Height patterns
            height_patterns = [
                r'height[:\s]+(\d+\.?\d*)',
                r'(\d+\.?\d*)\s*(?:feet|ft|foot|meters|m)?\s+(?:high|tall)',
                r'ceiling\s+height[:\s]+(\d+\.?\d*)'
            ]
            
            for pattern in height_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    try:
                        dimensions['height'] = float(match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue
        
        except Exception as e:
            print(f"Warning: Dimension extraction error: {e}")
        
        return dimensions
    
    def _extract_colors(self, text):
        """ENHANCED: Better color extraction with more patterns"""
        colors = {
            'north': None, 'south': None, 'east': None, 'west': None,
            'ceiling': None, 'floor': None, 'accent': None,
            'overall': []
        }
        
        text_lower = text.lower()
        
        try:
            # Directional walls
            for direction in ['north', 'south', 'east', 'west']:
                patterns = [
                    rf"{direction}\s+wall[^.!?]*?\b({'|'.join(re.escape(c) for c in self.all_colors)})\b",
                    rf"\b({'|'.join(re.escape(c) for c in self.all_colors)})\b[^.!?]*?{direction}\s+wall",
                    rf"{direction}\s*[:\-]\s*\b({'|'.join(re.escape(c) for c in self.all_colors)})\b",
                    rf"paint[^.!?]*?{direction}[^.!?]*?\b({'|'.join(re.escape(c) for c in self.all_colors)})\b"
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        for group in match.groups():
                            if group and group in self.all_colors:
                                colors[direction] = group
                                break
                        if colors[direction]:
                            break
            
            # Ceiling and floor
            for surface in ['ceiling', 'floor']:
                pattern = rf"{surface}[^.!?]*?\b({'|'.join(re.escape(c) for c in self.all_colors)})\b"
                match = re.search(pattern, text_lower)
                if match:
                    for group in match.groups():
                        if group and group in self.all_colors:
                            colors[surface] = group
                            break
            
            # Accent colors
            accent_pattern = rf"accent[^.!?]*?\b({'|'.join(re.escape(c) for c in self.all_colors)})\b"
            match = re.search(accent_pattern, text_lower)
            if match:
                for group in match.groups():
                    if group and group in self.all_colors:
                        colors['accent'] = group
                        break
            
            # Overall colors mentioned
            color_words = []
            for color in self.all_colors:
                if re.search(rf'\b{re.escape(color)}\b', text_lower):
                    color_words.append(color)
            
            colors['overall'] = list(set(color_words))
        
        except Exception as e:
            print(f"Warning: Color extraction error: {e}")
        
        return colors
    
    def _extract_furniture(self, text, room_type):
        """ENHANCED: Better furniture detection"""
        furniture_items = []
        text_lower = text.lower()
        
        try:
            if room_type and room_type in self.room_furniture:
                furniture_list = self.room_furniture[room_type]
            else:
                furniture_list = [item for items in self.room_furniture.values() for item in items]
            
            # Sort by length (longer phrases first to avoid partial matches)
            furniture_list_sorted = sorted(furniture_list, key=len, reverse=True)
            
            for item in furniture_list_sorted:
                if re.search(rf'\b{re.escape(item)}\b', text_lower):
                    furniture_items.append(item)
            
            # If nothing specific mentioned, use smart defaults
            if not furniture_items and room_type and room_type in self.room_furniture:
                furniture_items = self.room_furniture[room_type][:6]
        
        except Exception as e:
            print(f"Warning: Furniture extraction error: {e}")
        
        return list(set(furniture_items))
    
    def _extract_style(self, text):
        """ENHANCED: Better style detection"""
        text_lower = text.lower()
        
        try:
            # Sort styles by length (longer first)
            styles_sorted = sorted(self.styles, key=len, reverse=True)
            
            for style in styles_sorted:
                if re.search(rf'\b{re.escape(style)}\b', text_lower):
                    return style
        except Exception as e:
            print(f"Warning: Style extraction error: {e}")
        
        return 'modern'
    
    def _extract_materials(self, text):
        """NEW: Extract materials and textures"""
        materials_found = []
        text_lower = text.lower()
        
        try:
            for material in self.materials:
                if re.search(rf'\b{re.escape(material)}\b', text_lower):
                    materials_found.append(material)
        except Exception as e:
            print(f"Warning: Material extraction error: {e}")
        
        return list(set(materials_found))
    
    def _extract_lighting(self, text):
        """NEW: Extract lighting preferences"""
        lighting_found = []
        text_lower = text.lower()
        
        try:
            for lighting in self.lighting_types:
                if lighting in text_lower:
                    lighting_found.append(lighting)
        except Exception as e:
            print(f"Warning: Lighting extraction error: {e}")
        
        return list(set(lighting_found))
    
    def _extract_mood(self, text):
        """NEW: Extract mood and ambiance keywords"""
        mood_found = []
        text_lower = text.lower()
        
        try:
            for mood in self.mood_keywords:
                if re.search(rf'\b{re.escape(mood)}\b', text_lower):
                    mood_found.append(mood)
        except Exception as e:
            print(f"Warning: Mood extraction error: {e}")
        
        return list(set(mood_found))
    
    def _extract_special_requirements(self, text):
        """ENHANCED: More special requirements"""
        requirements = []
        text_lower = text.lower()
        
        try:
            # Storage needs
            if any(word in text_lower for word in ['storage', 'organized', 'organize']):
                requirements.append('ample storage')
            
            # Space characteristics
            if any(word in text_lower for word in ['open', 'spacious', 'airy']):
                requirements.append('open and spacious')
            
            if any(word in text_lower for word in ['cozy', 'intimate', 'small']):
                requirements.append('cozy and intimate')
            
            # Sustainability
            if any(word in text_lower for word in ['sustainable', 'eco', 'green', 'environmentally']):
                requirements.append('sustainable materials')
            
            # Accessibility
            if any(word in text_lower for word in ['accessible', 'wheelchair', 'ada']):
                requirements.append('accessibility features')
            
            # Technology
            if any(word in text_lower for word in ['smart', 'automated', 'technology']):
                requirements.append('smart home integration')
        
        except Exception as e:
            print(f"Warning: Special requirements error: {e}")
        
        return requirements
    
    def generate_design_prompt(self, parsed_data):
        """
        UPGRADED: Generate enhanced prompt for Stable Diffusion
        
        Now includes:
        - Materials
        - Lighting
        - Mood
        - More descriptive language
        """
        try:
            room_type = parsed_data.get('room_type', 'room')
            style = parsed_data.get('style', 'modern')
            colors = parsed_data.get('colors', {})
            furniture = parsed_data.get('furniture', [])
            materials = parsed_data.get('materials', [])
            lighting = parsed_data.get('lighting', [])
            mood = parsed_data.get('mood', [])
            
            # Build enhanced prompt
            prompt_parts = []
            
            # Main subject
            prompt_parts.append(f"A stunning {style} {room_type} interior design")
            
            # Mood/ambiance
            if mood:
                mood_desc = ' and '.join(mood[:2])
                prompt_parts.append(f"with a {mood_desc} atmosphere")
            
            # Colors
            if colors.get('overall'):
                color_desc = ', '.join(colors['overall'][:3])
                prompt_parts.append(f"featuring {color_desc} color scheme")
            
            # Directional walls (if specified)
            wall_descriptions = []
            for direction in ['north', 'south', 'east', 'west']:
                if colors.get(direction):
                    wall_descriptions.append(f"{direction} wall in {colors[direction]}")
            
            if wall_descriptions:
                prompt_parts.append(', '.join(wall_descriptions[:2]))
            
            # Furniture
            if furniture:
                furniture_desc = ', '.join(furniture[:5])
                prompt_parts.append(f"with {furniture_desc}")
            
            # Materials
            if materials:
                material_desc = ', '.join(materials[:3])
                prompt_parts.append(f"made of {material_desc}")
            
            # Lighting
            if lighting:
                light_desc = lighting[0]
                prompt_parts.append(f"{light_desc}")
            else:
                prompt_parts.append("natural lighting")
            
            # Quality descriptors (IMPORTANT for SD)
            quality_terms = [
                "professional interior photography",
                "architectural digest",
                "photorealistic",
                "8K UHD",
                "highly detailed",
                "perfect composition",
                "depth of field",
                "volumetric lighting"
            ]
            
            prompt_parts.extend(quality_terms)
            
            # Join all parts
            final_prompt = ', '.join(prompt_parts)
            
            # SD 2.1 can handle longer prompts better than SD 1.5
            # Limit to 500 characters to be safe
            if len(final_prompt) > 500:
                final_prompt = final_prompt[:500]
            
            return final_prompt
            
        except Exception as e:
            print(f"Error generating prompt: {e}")
            return "Professional interior design photograph, modern style, photorealistic, 8K resolution, beautiful lighting, architectural photography"
    
    def validate_prompt(self, user_prompt):
        """ENHANCED: Better validation"""
        required_elements = {
            'has_room_type': False,
            'has_color_or_material': False,
            'has_style_or_furniture_or_mood': False
        }
        
        try:
            prompt_lower = user_prompt.lower()
            
            # Room type
            for room in self.room_furniture.keys():
                if room in prompt_lower:
                    required_elements['has_room_type'] = True
                    break
            
            # Colors or materials
            has_color = any(color in prompt_lower for color in self.all_colors)
            has_material = any(material in prompt_lower for material in self.materials)
            required_elements['has_color_or_material'] = has_color or has_material
            
            # Style, furniture, or mood
            has_style = any(style in prompt_lower for style in self.styles)
            has_furniture = any(
                furniture in prompt_lower 
                for furniture_list in self.room_furniture.values() 
                for furniture in furniture_list
            )
            has_mood = any(mood in prompt_lower for mood in self.mood_keywords)
            
            required_elements['has_style_or_furniture_or_mood'] = has_style or has_furniture or has_mood
        
        except Exception as e:
            print(f"Error validating prompt: {e}")
        
        return required_elements