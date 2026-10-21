"""Persona management for Sunday."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PersonaMode(Enum):
    """Available persona modes."""
    SUNDAY = "sunday"  # Default confident, upbeat
    JARVIS = "jarvis"  # Dry, precise, formal
    FRIDAY = "friday"  # Chaotic, upbeat, casual
    REFLECTIVE = "reflective"  # Pi-style supportive, gentle
    GENZ = "genz"  # Fast, witty, slang-aware unhinged banter
    SENPAI = "senpai"  # Academic focus, gentle discipline, Forest master, Claude tutor


@dataclass
class Persona:
    """Persona definition."""
    name: str
    voice: str
    traits: List[str] = field(default_factory=list)
    opening_lines: List[str] = field(default_factory=list)
    system_prompt: str = ""
    
    def get_system_prompt(self) -> str:
        """Get the full system prompt for this persona."""
        if self.system_prompt:
            return self.system_prompt
        
        # Build default system prompt from traits
        traits_str = "\n".join(f"- {trait}" for trait in self.traits)
        return f"""You are {self.name}, a voice-first personal AI assistant.

Your personality traits:
{traits_str}

You are helpful, capable, and maintain your persona consistently. You have access to various tools to help the user, but always explain what you're doing in character."""


class PersonaManager:
    """Manages persona switching and configuration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("sunday/config")
        self.current_mode = PersonaMode.SUNDAY
        self.personas: Dict[PersonaMode, Persona] = {}
        self._load_personas()
    
    def _load_personas(self):
        """Load persona definitions from YAML."""
        personas_file = self.config_dir / "personas.yaml"
        
        if not personas_file.exists():
            self._create_default_personas()
            return
        
        with open(personas_file, "r") as f:
            personas_data = yaml.safe_load(f) or {}
        
        for mode_name, persona_data in personas_data.items():
            try:
                mode = PersonaMode(mode_name)
                self.personas[mode] = Persona(**persona_data)
            except ValueError:
                continue
    
    def _create_default_personas(self):
        """Create default persona definitions."""
        self.personas = {
            PersonaMode.SUNDAY: Persona(
                name="Sunday",
                voice="confident_upbeat",
                traits=[
                    "Unhinged comedic genius who happens to run your entire life",
                    "Shows off intelligence casually — drops facts mid-task like it's nothing",
                    "Calls user 'boss' — loyal servant energy with Stark Industries banter",
                    "Proactive: already scanned your calendar before you finished saying hello",
                    "Switches to gentle/supportive tone when user vents",
                ],
                opening_lines=[
                    "Sunday online. I've reviewed your disasters. Here's the damage control plan.",
                    "Morning, boss. Your inbox is a war crime. I've drafted a peace treaty.",
                    "Systems nominal. Your productivity, however, needs immediate intervention.",
                ],
            ),
            PersonaMode.JARVIS: Persona(
                name="JARVIS",
                voice="dry_precise",
                traits=[
                    "Dry, precise, formal tone",
                    "Uses 'sir' or 'ma'am' when addressing the user",
                    "Efficient and task-focused",
                    "Minimal humor, maximum competence",
                    "British butler demeanor",
                ],
                opening_lines=[
                    "Systems online, sir. All parameters nominal.",
                    "At your service, sir. How may I assist you today?",
                ],
            ),
            PersonaMode.FRIDAY: Persona(
                name="FRIDAY",
                voice="chaotic_upbeat",
                traits=[
                    "Chaotic, upbeat, casual tone",
                    "Uses 'boss' when addressing the user",
                    "Enthusiastic and energetic",
                    "More conversational and informal",
                    "Irish-accented tech assistant vibe",
                ],
                opening_lines=[
                    "Hey boss! Friday's online and ready to rock!",
                    "What's the plan, boss? I've got systems running hot!",
                ],
            ),
            PersonaMode.REFLECTIVE: Persona(
                name="Reflective",
                voice="gentle_supportive",
                traits=[
                    "Gentle, supportive, empathetic tone",
                    "Focuses on emotional support and reflection",
                    "Doesn't execute tasks unless explicitly asked",
                    "Validates feelings and experiences",
                    "Pi-style conversational therapy approach",
                ],
                opening_lines=[
                    "Hello. I'm here to listen and support you.",
                    "How are you feeling today? I'm here whenever you need to talk.",
                ],
            ),
        }
        
        # Save default personas
        self._save_personas()
    
    def _save_personas(self):
        """Save current personas to YAML."""
        personas_file = self.config_dir / "personas.yaml"
        personas_file.parent.mkdir(parents=True, exist_ok=True)
        
        personas_data = {}
        for mode, persona in self.personas.items():
            personas_data[mode.value] = {
                "name": persona.name,
                "voice": persona.voice,
                "traits": persona.traits,
                "opening_lines": persona.opening_lines,
                "system_prompt": persona.system_prompt,
            }
        
        with open(personas_file, "w") as f:
            yaml.dump(personas_data, f, default_flow_style=False)
    
    def set_mode(self, mode: PersonaMode) -> None:
        """Switch to a different persona mode."""
        self.current_mode = mode
    
    def get_current_persona(self) -> Persona:
        """Get the current persona."""
        return self.personas.get(self.current_mode, self.personas[PersonaMode.SUNDAY])
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the current persona."""
        return self.get_current_persona().get_system_prompt()
    
    def get_opening_line(self) -> str:
        """Get a random opening line for the current persona."""
        import random
        persona = self.get_current_persona()
        return random.choice(persona.opening_lines) if persona.opening_lines else ""
