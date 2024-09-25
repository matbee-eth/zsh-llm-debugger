import json
import ollama
import asyncio
import os
import subprocess
import shlex
import shutil
import logging
import sys
import platform
from typing import Any, Dict, List
from datetime import datetime

# Configure logging for verbose output
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for verbose logging
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to console
        logging.FileHandler("shell_debugger.log")  # Log to a file
    ]
)

# Function Definitions

def list_directory(path: str, options: List[str] = []) -> str:
    logging.debug(f"Entering list_directory with path: {path}, options: {options}")
    try:
        # Determine the operating system
        system = platform.system()
        logging.debug(f"Operating System detected: {system}")
        if system == "Windows":
            cmd = ['dir', path] + options
            shell = True
            logging.debug(f"Constructed command for Windows: {' '.join(cmd)}")
        else:
            cmd = ['ls', path] + options
            shell = False
            logging.debug(f"Constructed command for Unix: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=shell)
        logging.debug(f"Command output:\n{result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error listing directory: {e.stderr}")
        return f"Error listing directory: {e.stderr}"
    except Exception as e:
        logging.exception("Unexpected error in list_directory")
        return f"Unexpected error: {str(e)}"

def print_working_directory() -> str:
    logging.debug("Entering print_working_directory")
    try:
        cwd = os.getcwd()
        logging.debug(f"Current working directory: {cwd}")
        return cwd
    except Exception as e:
        logging.exception("Error getting current working directory")
        return f"Error getting current working directory: {str(e)}"

def list_processes(options: List[str] = []) -> str:
    logging.debug(f"Entering list_processes with options: {options}")
    try:
        # Determine the operating system
        system = platform.system()
        logging.debug(f"Operating System detected: {system}")
        if system == "Windows":
            cmd = ['tasklist'] + options
            shell = True
            logging.debug(f"Constructed command for Windows: {' '.join(cmd)}")
        else:
            cmd = ['ps'] + options
            shell = False
            logging.debug(f"Constructed command for Unix: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=shell)
        logging.debug(f"Command output:\n{result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error listing processes: {e.stderr}")
        return f"Error listing processes: {e.stderr}"
    except Exception as e:
        logging.exception("Unexpected error in list_processes")
        return f"Unexpected error: {str(e)}"

def display_file_contents(file_path: str) -> str:
    logging.debug(f"Entering display_file_contents with file_path: {file_path}")
    try:
        with open(file_path, 'r') as file:
            contents = file.read()
        logging.debug(f"Contents of {file_path}:\n{contents}")
        return contents
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return f"File not found: {file_path}"
    except Exception as e:
        logging.exception(f"Error reading file: {file_path}")
        return f"Error reading file: {str(e)}"

def execute_shell_command(command: str, env=os.environ) -> (str, str, int):
    """
    Executes a shell command and captures its output and exit status.
    """
    logging.debug(f"Executing shell command: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            executable='/bin/zsh',  # Ensure using ZSH
            env=env
        )
        logging.debug(f"Command executed with exit status: {result.returncode}")
        logging.debug(f"STDOUT:\n{result.stdout}")
        logging.debug(f"STDERR:\n{result.stderr}")
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        logging.exception("Error executing shell command")
        return '', str(e), 1

def gather_error_details(command: str, exit_status: int, stdout: str, stderr: str) -> Dict[str, Any]:
    """
    Gathers detailed error information, including system and environment details.
    """
    logging.debug("Gathering error details")
    try:
        details = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "exit_status": exit_status,
            "stdout": stdout,
            "stderr": stderr,
            "working_directory": os.getcwd(),
            "shell": os.getenv('SHELL', ''),
            "PATH": os.getenv('PATH', ''),
            "system_information": subprocess.getoutput('uname -a') if shutil.which('uname') else "System information not available",
            "os_release": subprocess.getoutput('cat /etc/os-release') if os.path.exists('/etc/os-release') else "OS release information not available",
            "command_binary_details": subprocess.getoutput(f'which {shlex.split(command)[0]}') if shutil.which(shlex.split(command)[0]) else "Command not found in PATH",
            "command_version": subprocess.getoutput(f'{shlex.split(command)[0]} --version') if shutil.which(shlex.split(command)[0]) else "Version information not available",
            "environment_variables": dict(os.environ)
        }
        logging.debug(f"Error details gathered: {details}")
        return details
    except Exception as e:
        logging.exception("Error gathering error details")
        return {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "exit_status": exit_status,
            "stdout": stdout,
            "stderr": stderr,
            "error": f"Error gathering error details: {str(e)}"
        }

# ALLOWED_FUNCTIONS Dictionary

ALLOWED_FUNCTIONS: Dict[str, Dict[str, Any]] = {
    "list_directory": {
        "name": "list_directory",
        "description": "List files and directories in a specified path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list."
                },
                "options": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["-la", "--help"]
                    },
                    "description": "Options to modify the behavior of the ls command."
                }
            },
            "required": ["path"]
        }
    },
    "print_working_directory": {
        "name": "print_working_directory",
        "description": "Print the current working directory.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    "list_processes": {
        "name": "list_processes",
        "description": "List currently running processes.",
        "parameters": {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["aux", "--help"]
                    },
                    "description": "Options to modify the behavior of the ps command."
                }
            }
        }
    },
    "display_file_contents": {
        "name": "display_file_contents",
        "description": "Display the contents of a specified file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to display."
                }
            },
            "required": ["file_path"]
        }
    }
}

# Mapping of function names to actual Python functions
AVAILABLE_FUNCTIONS: Dict[str, Any] = {
    "list_directory": list_directory,
    "print_working_directory": print_working_directory,
    "list_processes": list_processes,
    "display_file_contents": display_file_contents,
}

# Async Function to Interact with the Model

async def run(model: str, error_details: Dict[str, Any]):
    logging.debug("Starting interaction with the Ollama model")
    client = ollama.AsyncClient()

    # Define the system prompt for shell debugging
    system_prompt = {
        'role': 'system',
        'content': (
            "You are a shell debugger. Analyze the following failed shell command and provide a corrected command. "
            "Only respond with the corrected shell command, or by using a tool provided. You may not ask clarifying questions. "
            "You are expected to use the provided tools to answer the question."
        )
    }

    # Define six multi-turn few-shot examples
    few_shot_examples = [
        # Example 1
        {
            'role': 'user',
            'content': (
                "```sh\ncd /nonexistent_dir\n```\n"
                "Error Output:\n```\nbash: cd: /nonexistent_dir: No such file or directory\n```"
            )
        },
        {
            'role': 'assistant',
            'content': "",
            'tool_calls': [
                {
                    'function': {
                        'name': 'list_directory',
                        'arguments': {
                            'path': '/',
                            'options': ['-la']
                        }
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'content': "drwxr-xr-x  5 root root  4096 Apr 10 10:00 existing_dir\n..."
        },
        {
            'role': 'assistant',
            'content': "cd /existing_dir"
        },

        # Example 2
        {
            'role': 'user',
            'content': (
                "```sh\ngrep 'pattern'\n```\n"
                "Error Output:\n```\ngrep: missing file operand\nTry 'grep --help' for more information.\n```"
            )
        },
        {
            'role': 'assistant',
            'content': "",
            'tool_calls': [
                {
                    'function': {
                        'name': 'list_directory',
                        'arguments': {
                            'path': '.',
                            'options': ['-la']
                        }
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'content': "file1.txt\nfile2.log\nscript.sh\n"
        },
        {
            'role': 'assistant',
            'content': "grep 'pattern' file1.txt"
        },

        # Example 3
        {
            'role': 'user',
            'content': (
                "```sh\ncat /etc/hostsh\n```\n"
                "Error Output:\n```\nbash: cat: /etc/hostsh: No such file or directory\n```"
            )
        },
        {
            'role': 'assistant',
            'content': "",
            'tool_calls': [
                {
                    'function': {
                        'name': 'list_directory',
                        'arguments': {
                            'path': '/etc',
                            'options': []
                        }
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'content': "hosts\nhostname\nresolv.conf\n"
        },
        {
            'role': 'assistant',
            'content': "cat /etc/hosts"
        },

        # Example 4
        {
            'role': 'user',
            'content': (
                "```sh\npython script.py\n```\n"
                "Error Output:\n```\npython: command not found\n```"
            )
        },
        {
            'role': 'assistant',
            'content': "",
            'tool_calls': [
                {
                    'function': {
                        'name': 'list_processes',
                        'arguments': {
                            'options': ['aux']
                        }
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'content': "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n..."
        },
        {
            'role': 'assistant',
            'content': "python3 script.py"
        },

        # Example 5
        {
            'role': 'user',
            'content': (
                "```sh\nmkdir new_folder\n```\n"
                "Error Output:\n```\nmkdir: cannot create directory 'new_folder': Permission denied\n```"
            )
        },
        {
            'role': 'assistant',
            'content': "",
            'tool_calls': [
                {
                    'function': {
                        'name': 'print_working_directory',
                        'arguments': {}
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'content': "/home/user/projects"
        },
        {
            'role': 'assistant',
            'content': "sudo mkdir new_folder"
        },

        # Example 6
        {
            'role': 'user',
            'content': (
                "```sh\nrm *.txt\n```\n"
                "Error Output:\n```\nrm: missing operand after '*.txt'\nTry 'rm --help' for more information.\n```"
            )
        },
        {
            'role': 'assistant',
            'content': "",
            'tool_calls': [
                {
                    'function': {
                        'name': 'list_directory',
                        'arguments': {
                            'path': '.',
                            'options': ['-la']
                        }
                    }
                }
            ]
        },
        {
            'role': 'tool',
            'content': "file1.txt\nfile2.txt\nREADME.md\n"
        },
        {
            'role': 'assistant',
            'content': "rm *.txt"
        },
    ]

    # Construct the user message as per the interaction pattern
    user_message = {
        'role': 'user',
        'content': (
            f"```sh\n{error_details['command']}\n```\n"
            f"Error Output:\n```\n{error_details['stderr']}\n```"
        )
    }

    # Initialize conversation with system prompt and few-shot examples
    messages = [system_prompt] + few_shot_examples + [user_message]

    logging.debug("Conversation initialized with system prompt, few-shot examples, and user message")

    # First API call: Send the messages and function descriptions to the model
    try:
        logging.debug("Sending first API call to the model with messages and tools")
        response = await client.chat(
            model=model,
            messages=messages,
            tools=list(ALLOWED_FUNCTIONS.values()),
        )
        logging.debug("Received response from the model")
    except Exception as e:
        logging.exception("Error during the first API call to the model")
        print(f"Error communicating with the model: {str(e)}", file=sys.stderr)
        return

    # Add the model's response to the conversation history
    messages.append(response['message'])

    # Check if the model decided to use any provided function
    if not response['message'].get('tool_calls'):
        logging.debug("The model didn't use any function")
        print(response['message']['content'])
        return

    # Process function calls made by the model
    if response['message'].get('tool_calls'):
        for tool in response['message']['tool_calls']:
            function_name = tool['function']['name']
            function_args = tool['function']['arguments']
            logging.debug(f"Processing tool call: {function_name} with arguments: {function_args}")

            if function_name in AVAILABLE_FUNCTIONS:
                function_to_call = AVAILABLE_FUNCTIONS[function_name]
                try:
                    if function_name == "list_directory":
                        path = function_args['path']
                        options = function_args.get('options', [])
                        logging.debug(f"Calling list_directory with path: {path}, options: {options}")
                        function_response = function_to_call(path, options)
                    elif function_name == "print_working_directory":
                        logging.debug("Calling print_working_directory")
                        function_response = function_to_call()
                    elif function_name == "list_processes":
                        options = function_args.get('options', [])
                        logging.debug(f"Calling list_processes with options: {options}")
                        function_response = function_to_call(options)
                    elif function_name == "display_file_contents":
                        file_path = function_args['file_path']
                        logging.debug(f"Calling display_file_contents with file_path: {file_path}")
                        function_response = function_to_call(file_path)
                    else:
                        logging.warning(f"Function '{function_name}' is not implemented")
                        function_response = f"Function '{function_name}' is not implemented."
                except Exception as e:
                    logging.exception(f"Error executing function '{function_name}'")
                    function_response = f"Error executing function '{function_name}': {str(e)}"

                # Add function response to the conversation
                messages.append(
                    {
                        'role': 'tool',
                        'content': function_response,
                    }
                )
                logging.debug(f"Function '{function_name}' executed successfully")
            else:
                logging.warning(f"Function '{function_name}' is not allowed")
                function_response = f"Function '{function_name}' is not allowed."
                messages.append(
                    {
                        'role': 'tool',
                        'content': function_response,
                    }
                )

    # Second API call: Get final response from the model
    try:
        logging.debug("Sending second API call to the model with updated messages")
        final_response = await client.chat(model=model, messages=messages)
        logging.debug("Received final response from the model")
        print(final_response['message']['content'])
    except Exception as e:
        logging.exception("Error during the second API call to the model")
        print(f"Error communicating with the model: {str(e)}", file=sys.stderr)

# Main Execution Flow

def main():
    logging.debug("Starting main execution flow")

    # Check if a JSON file path is provided
    if len(sys.argv) != 2:
        logging.error("Usage: python ollama_debugger.py <error_details_json_file>")
        print("Usage: python ollama_debugger.py <error_details_json_file>")
        sys.exit(1)

    # Load error details from the provided JSON file
    error_details_file = sys.argv[1]
    if not os.path.exists(error_details_file):
        logging.error(f"Error details file not found: {error_details_file}")
        print(f"Error details file not found: {error_details_file}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(error_details_file, 'r') as f:
            file_contents = f.read()
            error_details = json.loads(file_contents)
        logging.debug(f"Loaded error details: {error_details}")
    except json.JSONDecodeError as e:
        logging.exception(f"JSON decoding failed for file: {error_details_file}")
        print(f"JSON decoding failed: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Error reading error details file: {error_details_file}")
        print(f"Error reading error details file: {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Run the async function to interact with the model
    asyncio.run(run('llama3.1:8b', error_details))

# Run the main function
if __name__ == "__main__":
    main()
