#!/usr/bin/env python3
"""
txAdmin Recipe Processor
Processes txAdminRecipe.yaml files and replicates the folder structure locally
"""

import os
import sys
import yaml
import requests
import zipfile
import shutil
import argparse
import subprocess
import tempfile
import time
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional

class TxAdminRecipeProcessor:
    def __init__(self, recipe_file: str, output_dir: str, verbose: bool = False, dry_run: bool = False):
        self.recipe_file = recipe_file
        self.output_dir = Path(output_dir).resolve()
        self.verbose = verbose
        self.dry_run = dry_run
        self.temp_dir = None
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temp directory for downloads (not needed in dry-run mode)
        if not self.dry_run:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="txrecipe_"))
        else:
            self.temp_dir = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with optional verbosity"""
        prefix = "[DRY-RUN] " if self.dry_run else ""
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"{prefix}[{level}] {message}")
    
    def _should_create_in_dry_run(self, path: Path) -> Path:
        """Determine the parent folder structure that should be created in dry-run mode.
        Only creates folders with [brackets], not the final resource folder."""
        parts = path.parts
        parent_parts = []
        
        for part in parts:
            # Include all parts up to but not including the final resource name
            # Only include parts that contain brackets or are standard paths
            if '[' in part and ']' in part:
                parent_parts.append(part)
            elif part in ['resources', 'tmp'] or part.startswith('./'):
                parent_parts.append(part)
            else:
                # This is likely the resource folder name - don't include it
                break
        
        return Path(*parent_parts) if parent_parts else Path()
    
    def _is_commit_hash(self, ref: str) -> bool:
        """Check if a ref looks like a commit hash (SHA)."""
        return len(ref) >= 7 and re.match(r'^[a-f0-9]+$', ref.lower()) is not None
    
    def _retry_operation(self, operation, max_retries=3, delay=2):
        """Retry an operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = delay * (2 ** attempt)
                self.log(f"Attempt {attempt + 1} failed: {e}", "WARNING")
                self.log(f"Retrying in {wait_time} seconds...", "INFO")
                time.sleep(wait_time)
    
    def cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.log(f"Cleaned up temporary directory: {self.temp_dir}")
        elif self.dry_run:
            self.log("No cleanup needed in dry-run mode")
    
    def load_recipe(self) -> Dict[str, Any]:
        """Load and parse the txAdmin recipe YAML file"""
        try:
            with open(self.recipe_file, 'r') as f:
                content = f.read()
                # Handle special txAdmin variables (treat them as comments for now)
                lines = content.split('\n')
                filtered_lines = []
                for line in lines:
                    if not line.strip().startswith('$'):
                        filtered_lines.append(line)
                content = '\n'.join(filtered_lines)
                
                recipe = yaml.safe_load(content)
                self.log(f"Loaded recipe: {recipe.get('name', 'Unknown')}")
                return recipe
        except Exception as e:
            self.log(f"Failed to load recipe file: {e}", "ERROR")
            sys.exit(1)
    
    def process_download_github(self, task: Dict[str, Any]) -> bool:
        """Process download_github action"""
        src = task.get('src', '')
        dest = task.get('dest', '')
        ref = task.get('ref', 'main')
        subpath = task.get('subpath', '')
        
        if not src or not dest:
            self.log(f"Missing src or dest in download_github task", "WARNING")
            return False
        
        # Resolve destination path first
        dest_path = self.output_dir / dest.lstrip('./')
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle placeholder URLs in dry-run mode
        if self.dry_run:
            # Only create parent directories with [brackets], not the resource folder itself
            parent_path = self._should_create_in_dry_run(dest_path)
            if parent_path and str(parent_path) != '.':
                full_parent = self.output_dir / parent_path
                full_parent.mkdir(parents=True, exist_ok=True)
                self.log(f"Created parent structure: {full_parent}")
            
            # Extract resource name for logging
            resource_name = dest_path.name
            
            if src == '<GITHUB_URL>':
                # This is a placeholder URL
                subpath_info = f" (subpath: {subpath})" if subpath else ""
                self.log(f"Would clone [PLACEHOLDER_URL] → {resource_name} (ref: {ref}){subpath_info}")
                self.log(f"  Target location: {dest_path}")
            else:
                # Try to extract repo info from actual URL
                parts = urlparse(src)
                path_parts = parts.path.strip('/').split('/')
                if len(path_parts) >= 2:
                    owner = path_parts[0]
                    repo = path_parts[1]
                    subpath_info = f" (subpath: {subpath})" if subpath else ""
                    self.log(f"Would clone {owner}/{repo} (ref: {ref}){subpath_info} → {resource_name}")
                    self.log(f"  Target location: {dest_path}")
                else:
                    # Invalid URL format - warn but don't fail
                    self.log(f"Would clone [INVALID_URL: {src}] → {resource_name}", "WARNING")
                    self.log(f"  Target location: {dest_path}")
            return True
        
        # For actual cloning, validate the URL
        parts = urlparse(src)
        path_parts = parts.path.strip('/').split('/')
        if len(path_parts) < 2 or src == '<GITHUB_URL>':
            self.log(f"Invalid GitHub URL: {src}", "WARNING")
            return False
        
        owner = path_parts[0]
        repo = path_parts[1]
        
        self.log(f"Cloning {owner}/{repo} (ref: {ref}) to {dest_path}")
        
        # Clone the repository
        temp_clone_dir = self.temp_dir / f"{owner}_{repo}_{ref}"
        
        try:
            # Determine the best cloning strategy based on ref type
            if self._is_commit_hash(ref):
                # For commit hashes, clone full repo then checkout
                self.log(f"Detected commit hash, cloning full repository...")
                cmd = ['git', 'clone', src, str(temp_clone_dir)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    # Checkout the specific commit
                    checkout_result = subprocess.run(
                        ['git', 'checkout', ref], 
                        cwd=temp_clone_dir, 
                        capture_output=True, 
                        text=True,
                        timeout=60
                    )
                    if checkout_result.returncode != 0:
                        self.log(f"Failed to checkout {ref}: {checkout_result.stderr}", "ERROR")
                        return False
            else:
                # For branch names, try shallow clone first
                self.log(f"Attempting shallow clone of branch '{ref}'...")
                cmd = ['git', 'clone', '--depth', '1', '--branch', ref, src, str(temp_clone_dir)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    # Fallback: try without branch specification (use default branch)
                    self.log(f"Shallow clone failed, trying default branch...")
                    cmd = ['git', 'clone', '--depth', '1', src, str(temp_clone_dir)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0 and ref not in ['main', 'master']:
                        # Try to checkout the ref if it exists
                        checkout_result = subprocess.run(
                            ['git', 'checkout', ref], 
                            cwd=temp_clone_dir, 
                            capture_output=True, 
                            text=True,
                            timeout=60
                        )
                        if checkout_result.returncode != 0:
                            self.log(f"Warning: Could not checkout '{ref}', using default branch", "WARNING")
            
            if result.returncode != 0:
                self.log(f"Failed to clone repository {src}: {result.stderr}", "ERROR")
                return False
            
            # Remove .git directory to save space
            git_dir = temp_clone_dir / '.git'
            if git_dir.exists():
                shutil.rmtree(git_dir)
            
            # Handle subpath if specified
            source_dir = temp_clone_dir
            if subpath:
                source_dir = temp_clone_dir / subpath
                if not source_dir.exists():
                    self.log(f"Subpath '{subpath}' not found in repository {owner}/{repo}", "ERROR")
                    self.log(f"Available paths in repository:", "INFO")
                    try:
                        for item in sorted(temp_clone_dir.rglob('*')):
                            if item.is_dir() and not str(item.name).startswith('.'):
                                rel_path = item.relative_to(temp_clone_dir)
                                self.log(f"  {rel_path}", "INFO")
                    except Exception:
                        self.log(f"  Could not list repository contents", "INFO")
                    return False
            
            # Move to destination
            if dest_path.exists():
                shutil.rmtree(dest_path)
            
            if subpath:
                # If subpath is specified, copy only that directory's contents
                shutil.copytree(source_dir, dest_path)
            else:
                # Otherwise, move the entire repo
                shutil.move(str(temp_clone_dir), str(dest_path))
            
            self.log(f"Successfully cloned {owner}/{repo} to {dest_path}")
            return True
            
        except subprocess.TimeoutExpired:
            self.log(f"Timeout while cloning repository {src}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error processing GitHub download {src}: {e}", "ERROR")
            return False
    
    def process_download_file(self, task: Dict[str, Any]) -> bool:
        """Process download_file action"""
        url = task.get('url', '')
        path = task.get('path', '')
        
        if not url or not path:
            self.log(f"Missing url or path in download_file task", "WARNING")
            return False
        
        # Resolve destination path
        dest_path = self.output_dir / path.lstrip('./')
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.dry_run:
            # In dry-run mode, just create the parent directory
            self.log(f"Would download {url} to {dest_path}")
            return True
        
        self.log(f"Downloading {url} to {dest_path}")
        
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.log(f"Successfully downloaded {url}")
            return True
            
        except Exception as e:
            self.log(f"Error downloading file: {e}", "ERROR")
            return False
    
    def process_unzip(self, task: Dict[str, Any]) -> bool:
        """Process unzip action"""
        src = task.get('src', '')
        dest = task.get('dest', '')
        
        if not src or not dest:
            self.log(f"Missing src or dest in unzip task", "WARNING")
            return False
        
        # Resolve paths
        src_path = self.output_dir / src.lstrip('./')
        dest_path = self.output_dir / dest.lstrip('./')
        
        if self.dry_run:
            # In dry-run mode, just create the destination directory
            dest_path.mkdir(parents=True, exist_ok=True)
            self.log(f"Would extract {src_path} to {dest_path}")
            return True
        
        if not src_path.exists():
            self.log(f"Source zip file not found: {src_path}", "WARNING")
            return False
        
        dest_path.mkdir(parents=True, exist_ok=True)
        
        self.log(f"Extracting {src_path} to {dest_path}")
        
        try:
            with zipfile.ZipFile(src_path, 'r') as zip_ref:
                zip_ref.extractall(dest_path)
            
            self.log(f"Successfully extracted {src_path}")
            return True
            
        except Exception as e:
            self.log(f"Error extracting zip file: {e}", "ERROR")
            return False
    
    def process_move_path(self, task: Dict[str, Any]) -> bool:
        """Process move_path action"""
        src = task.get('src', '')
        dest = task.get('dest', '')
        overwrite = task.get('overwrite', False)
        
        if not src or not dest:
            self.log(f"Missing src or dest in move_path task", "WARNING")
            return False
        
        # Resolve paths
        src_path = self.output_dir / src.lstrip('./')
        dest_path = self.output_dir / dest.lstrip('./')
        
        if self.dry_run:
            # In dry-run mode, just create the destination directory structure
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            overwrite_info = " (overwrite)" if overwrite else ""
            self.log(f"Would move {src_path} to {dest_path}{overwrite_info}")
            return True
        
        if not src_path.exists():
            self.log(f"Source path not found: {src_path}", "WARNING")
            return False
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.log(f"Moving {src_path} to {dest_path}")
        
        try:
            if dest_path.exists():
                if overwrite:
                    if dest_path.is_dir():
                        shutil.rmtree(dest_path)
                    else:
                        dest_path.unlink()
                else:
                    self.log(f"Destination already exists and overwrite is False: {dest_path}", "WARNING")
                    return False
            
            shutil.move(str(src_path), str(dest_path))
            self.log(f"Successfully moved {src_path} to {dest_path}")
            return True
            
        except Exception as e:
            self.log(f"Error moving path: {e}", "ERROR")
            return False
    
    def process_remove_path(self, task: Dict[str, Any]) -> bool:
        """Process remove_path action"""
        path = task.get('path', '')
        
        if not path:
            self.log(f"Missing path in remove_path task", "WARNING")
            return False
        
        # Resolve path
        target_path = self.output_dir / path.lstrip('./')
        
        if self.dry_run:
            # In dry-run mode, just log what would be removed
            self.log(f"Would remove {target_path}")
            return True
        
        if not target_path.exists():
            self.log(f"Path to remove not found: {target_path}", "WARNING")
            return True  # Not an error if it doesn't exist
        
        self.log(f"Removing {target_path}")
        
        try:
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
            
            self.log(f"Successfully removed {target_path}")
            return True
            
        except Exception as e:
            self.log(f"Error removing path: {e}", "ERROR")
            return False
    
    def process_waste_time(self, task: Dict[str, Any]) -> bool:
        """Process waste_time action (throttling)"""
        seconds = task.get('seconds', 0)
        
        if seconds > 0:
            if self.dry_run:
                self.log(f"Would wait {seconds} seconds (throttling)")
            else:
                self.log(f"Waiting {seconds} seconds (throttling)...")
                time.sleep(seconds)
        
        return True
    
    def process_task(self, task: Dict[str, Any]) -> bool:
        """Process a single task based on its action type"""
        action = task.get('action', '')
        
        # Skip database-related actions
        if action in ['connect_database', 'query_database']:
            self.log(f"Skipping database action: {action}")
            return True
        
        # Map actions to their processors
        action_map = {
            'download_github': self.process_download_github,
            'download_file': self.process_download_file,
            'unzip': self.process_unzip,
            'move_path': self.process_move_path,
            'remove_path': self.process_remove_path,
            'waste_time': self.process_waste_time,
        }
        
        processor = action_map.get(action)
        if processor:
            return processor(task)
        else:
            self.log(f"Unknown action type: {action}", "WARNING")
            return False
    
    def process(self):
        """Main processing function"""
        recipe = self.load_recipe()
        
        tasks = recipe.get('tasks', [])
        if not tasks:
            self.log("No tasks found in recipe", "WARNING")
            return
        
        total_tasks = len(tasks)
        successful = 0
        failed = 0
        skipped = 0
        
        mode_text = "DRY-RUN MODE: Creating folder structure" if self.dry_run else "Processing"
        print(f"\n{mode_text} for {total_tasks} tasks...")
        print("=" * 60)
        
        if self.dry_run:
            print("Note: Dry-run will only create parent folders with [brackets]")
            print("Resource folders will be created during actual clone operations")
            print("=" * 60)
        
        for i, task in enumerate(tasks, 1):
            # Check if task is commented (None value from YAML)
            if task is None:
                skipped += 1
                continue
            
            action = task.get('action', 'unknown')
            dest = task.get('dest', task.get('path', 'unknown'))
            progress_percent = round((i / total_tasks) * 100)
            print(f"\n[{i}/{total_tasks}] ({progress_percent}%) Processing: {action}")
            if dest != 'unknown':
                print(f"  → {dest}")
            
            if self.process_task(task):
                successful += 1
                print(f"✓ Success")
            else:
                failed += 1
                print(f"✗ Failed")
        
        print("\n" + "=" * 60)
        print(f"Results: {successful} successful, {failed} failed, {skipped} skipped")
        print(f"Output directory: {self.output_dir}")
        
        # Cleanup
        self.cleanup()

def main():
    parser = argparse.ArgumentParser(description='Process txAdmin recipe files')
    parser.add_argument('recipe', nargs='?', default='txAdminRecipe.yaml',
                        help='Path to the txAdminRecipe.yaml file')
    parser.add_argument('-o', '--output', default='./fivem-server',
                        help='Output directory for the server files')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--dry-run', action='store_true',
                        help='Create folder structure without cloning repositories')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.recipe):
        print(f"Error: Recipe file not found: {args.recipe}")
        sys.exit(1)
    
    processor = TxAdminRecipeProcessor(args.recipe, args.output, args.verbose, args.dry_run)
    
    try:
        processor.process()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        processor.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        processor.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main() 