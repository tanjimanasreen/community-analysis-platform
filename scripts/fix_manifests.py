import sys
import json
import hashlib
from pathlib import Path

def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def fix_manifests(api_root: Path):
    runs_dir = api_root / "runs"
    if not runs_dir.exists():
        return
        
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
            
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            continue
            
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        modified = False
        for artifact in manifest.get("artifacts", []):
            file_path = run_dir / artifact["path"]
            if not file_path.exists():
                continue
                
            actual_size = file_path.stat().st_size
            actual_hash = hash_file(file_path)
            
            if artifact.get("byte_size") != actual_size or artifact.get("sha256") != actual_hash:
                print(f"Updating manifest for {artifact['key']} in run {run_dir.name}")
                artifact["byte_size"] = actual_size
                artifact["sha256"] = actual_hash
                modified = True
                
        if modified:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
                # Wait, I need to use json.dump
                json.dump(manifest, f, indent=2, sort_keys=True, ensure_ascii=False)
                f.write("\n")
            print(f"Saved manifest for {run_dir.name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_manifests.py <API_ROOT>")
        sys.exit(1)
    fix_manifests(Path(sys.argv[1]))
