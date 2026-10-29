from dataclasses import dataclass, field


@dataclass
class EditorTab:
    dalvik_class : str
    title : str
    kind : str = "class"
    dex_name : str = ""
    source : str = ""
    edited_source : str = ""
    loading : bool = True
    error : str = ""
    yview : tuple = (0.0, 1.0)
    xview : tuple = (0.0, 1.0)
    insert_index : str = "1.0"
    comments : dict = field(default_factory=dict)
    member_references : list = field(default_factory=list)
    rendered_member_references : list = field(default_factory=list)
