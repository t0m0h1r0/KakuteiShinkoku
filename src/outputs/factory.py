from typing import Dict, Any
from pathlib import Path
from .console_output import ConsoleOutput, ColorConsoleOutput, ImprovedConsoleOutput
from .file_output import FileOutput, AppendFileOutput, LogFileOutput

def create_output(output_type: str = 'console', **kwargs) -> Any:
    """出力オブジェクトを作成"""
    if output_type == 'console':
        use_color = kwargs.get('use_color', False)
        formatter = kwargs.get('formatter')
        return (
            ColorConsoleOutput(formatter) if use_color else 
            ImprovedConsoleOutput(formatter)
        )
    
    elif output_type == 'file':
        output_path = kwargs.get('output_path')
        if not output_path:
            raise ValueError("output_path is required for file output")
        
        append_mode = kwargs.get('append', False)
        formatter = kwargs.get('formatter')
        
        if append_mode:
            return AppendFileOutput(output_path, formatter)
        return FileOutput(output_path, formatter)
    
    elif output_type == 'log':
        output_path = kwargs.get('output_path')
        if not output_path:
            raise ValueError("output_path is required for log output")
        
        formatter = kwargs.get('formatter')
        log_output = LogFileOutput(output_path, formatter)
        
        if 'prefix' in kwargs:
            log_output.set_line_prefix(kwargs['prefix'])
        
        return log_output
    
    raise ValueError(f"Unknown output type: {output_type}")