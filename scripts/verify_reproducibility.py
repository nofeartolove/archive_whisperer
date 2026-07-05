import os
import sys
import shutil
import subprocess
import tempfile
import pathlib

# ANSI colors for clear output formatting
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_banner(text: str):
    print(f"\n{BLUE}=================================================={RESET}")
    print(f"{BLUE}>>> {text}{RESET}")
    print(f"{BLUE}=================================================={RESET}")

def main():
    original_root = pathlib.Path(__file__).parent.parent.resolve()
    
    print_banner("ARCHIVE WHISPERER - REPRODUCIBILITY AUDIT")
    print(f"Original Workspace: {original_root}")
    
    # 1. Create a temporary isolated directory inside the workspace
    # (avoiding system temp folder to respect user constraints)
    temp_dir = original_root / "temp_reproduce_check"
    if temp_dir.exists():
        print(f"{YELLOW}Cleaning up existing check directory: {temp_dir}{RESET}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    os.makedirs(temp_dir, exist_ok=True)
    print(f"Created isolated reproduction directory: {temp_dir}")
    
    # 2. Simulate fresh clone by copying git-tracked files only
    print(f"\n{BLUE}Copying git-tracked files...{RESET}")
    try:
        git_files_raw = subprocess.check_output(
            ["git", "ls-files"], cwd=str(original_root)
        ).decode("utf-8").splitlines()
        
        for f in git_files_raw:
            src_file = original_root / f
            dest_file = temp_dir / f
            os.makedirs(dest_file.parent, exist_ok=True)
            shutil.copy2(src_file, dest_file)
            
        print(f"{GREEN}PASS: Successfully cloned {len(git_files_raw)} tracked files.{RESET}")
    except Exception as e:
        print(f"{RED}FAIL: Failed to clone git-tracked files: {e}{RESET}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)
        
    # 3. Create fresh virtual environment
    print_banner("1. CREATING VIRTUAL ENVIRONMENT")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", ".venv"], cwd=str(temp_dir))
        print(f"{GREEN}PASS: Virtual environment created successfully.{RESET}")
    except Exception as e:
        print(f"{RED}FAIL: Failed to create virtual environment: {e}{RESET}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)
        
    # Determine python & pip paths for virtual environment
    if sys.platform == "win32":
        venv_python = temp_dir / ".venv" / "Scripts" / "python.exe"
        venv_pip = temp_dir / ".venv" / "Scripts" / "pip.exe"
    else:
        venv_python = temp_dir / ".venv" / "bin" / "python"
        venv_pip = temp_dir / ".venv" / "bin" / "pip"
        
    # 4. Install dependencies
    print_banner("2. INSTALLING DEPENDENCIES")
    try:
        subprocess.check_call([str(venv_pip), "install", "-r", "requirements.txt"], cwd=str(temp_dir))
        print(f"{GREEN}PASS: Dependencies installed successfully.{RESET}")
    except Exception as e:
        print(f"{RED}FAIL: Dependency installation failed: {e}{RESET}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)
        
    # 5. Run pytest and assert it passes BEFORE API key is configured
    print_banner("3. RUNNING OFFLINE TEST SUITE (pytest)")
    try:
        # Run pytest offline
        subprocess.check_call([str(venv_python), "-m", "pytest"], cwd=str(temp_dir))
        print(f"{GREEN}PASS: Test suite completed with zero failures (offline mode).{RESET}")
    except Exception as e:
        print(f"{RED}FAIL: Test suite failed or raised errors: {e}{RESET}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)
        
    # 6. Optionally run live pipeline check if GOOGLE_API_KEY is in context
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        print_banner("4. RUNNING LIVE PIPELINE ACCURACY CHECKS")
        print(f"Found GOOGLE_API_KEY environment variable. Running single-page sanity check...")
        
        # Write .env file in temp folder for validation run
        env_content = f"GOOGLE_API_KEY={api_key}\n"
        loc_key = os.environ.get("LOC_API_KEY")
        if loc_key:
            env_content += f"LOC_API_KEY={loc_key}\n"
        (temp_dir / ".env").write_text(env_content, encoding="utf-8")
        
        try:
            # We run test_gibson_page011 check
            test_run_script = temp_dir / "scripts" / "run_pipeline_test.py"
            # Modify to run Gibson Page 11 only for rapid verification
            script_content = test_run_script.read_text(encoding="utf-8")
            # Replace main block to execute Gibson Page 11 only
            page_11_only_block = """
def main():
    print("Running reproducibility sanity check on Page 11...")
    run_single_page_test("Gibson Page 11", "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:011/full/pct:100/0/default.jpg")

if __name__ == "__main__":
    main()
"""
            # Truncate and replace the original test run main block
            lines = script_content.splitlines()
            main_idx = -1
            for idx, line in enumerate(lines):
                if "def main():" in line:
                    main_idx = idx
                    break
            if main_idx != -1:
                new_content = "\n".join(lines[:main_idx]) + "\n" + page_11_only_block
                test_run_script.write_text(new_content, encoding="utf-8")
            
            subprocess.check_call([str(venv_python), "scripts/run_pipeline_test.py"], cwd=str(temp_dir))
            print(f"{GREEN}PASS: Live pipeline completed successfully on Gibson Page 11.{RESET}")
        except Exception as e:
            print(f"{RED}FAIL: Live pipeline run failed: {e}{RESET}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            sys.exit(1)
    else:
        print_banner("4. RUNNING LIVE PIPELINE ACCURACY CHECKS (SKIPPED)")
        print(f"{YELLOW}No GOOGLE_API_KEY found in context environment. Skipping live check.{RESET}")
        print("To run live verification, export GOOGLE_API_KEY first.")
        
    # Cleanup temp directory upon successful run
    print(f"\n{BLUE}Cleaning up reproduction test files...{RESET}")
    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"{GREEN}PASS: Isolated folder deleted. Workspace clean.{RESET}")
    
    print(f"\n{GREEN}=================================================={RESET}")
    print(f"{GREEN}>>> REPRODUCIBILITY VERIFICATION SUCCESSFUL! <<<{RESET}")
    print(f"{GREEN}=================================================={RESET}")

if __name__ == "__main__":
    main()
