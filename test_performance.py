#!/usr/bin/env python3
"""
Performance test script for Video Labels Organizer.

This script compares the performance of the old serial system
with the new concurrent system.
"""

import asyncio
import time
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any

# Import both old and new systems
try:
    from src.media_organiser import organize_files as old_organize_files
    from src.performant_media_organiser import organize_files_sync as new_organize_files
    OLD_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import old system: {e}")
    OLD_SYSTEM_AVAILABLE = False


def create_test_files(directory: str, count: int = 10) -> List[str]:
    """Create test video files for performance testing."""
    test_dir = Path(directory)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test files with realistic names
    test_files = []
    for i in range(count):
        # Create different types of media files
        if i % 3 == 0:
            # Movie files
            filename = f"Movie_{i:02d}_2023.mp4"
        elif i % 3 == 1:
            # TV show files
            filename = f"Show_Name_S01E{i:02d}_Episode_Title.mp4"
        else:
            # Special files
            filename = f"Show_Name_S00E{i:02d}_Special.mp4"
        
        file_path = test_dir / filename
        # Create empty file (for testing purposes)
        file_path.touch()
        test_files.append(str(file_path))
    
    return test_files


def test_old_system(source: str, target: str) -> Dict[str, Any]:
    """Test the old serial system."""
    if not OLD_SYSTEM_AVAILABLE:
        return {"error": "Old system not available"}
    
    print("Testing old serial system...")
    start_time = time.time()
    
    try:
        # Use dry_run to avoid actual file operations
        old_organize_files(source, target, dry_run=True)
        end_time = time.time()
        
        return {
            "success": True,
            "time": end_time - start_time,
            "system": "old"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "time": time.time() - start_time,
            "system": "old"
        }


def test_new_system(source: str, target: str) -> Dict[str, Any]:
    """Test the new concurrent system."""
    print("Testing new concurrent system...")
    start_time = time.time()
    
    try:
        # Use dry_run to avoid actual file operations
        results = new_organize_files(source, target, dry_run=True)
        end_time = time.time()
        
        return {
            "success": True,
            "time": end_time - start_time,
            "system": "new",
            "files_processed": len(results) if results else 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "time": time.time() - start_time,
            "system": "new"
        }


async def test_async_system(source: str, target: str) -> Dict[str, Any]:
    """Test the new async system."""
    print("Testing new async system...")
    start_time = time.time()
    
    try:
        from src.performant_media_organiser import PerformantMediaOrganiser
        
        async with PerformantMediaOrganiser(max_workers=8) as organizer:
            results = await organizer.organize_files(source, target, dry_run=True)
            stats = organizer.get_performance_stats()
            
        end_time = time.time()
        
        return {
            "success": True,
            "time": end_time - start_time,
            "system": "async",
            "files_processed": stats['files_processed'],
            "ffprobe_calls": stats['ffprobe_calls'],
            "errors": stats['errors']
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "time": time.time() - start_time,
            "system": "async"
        }


def print_results(results: List[Dict[str, Any]]):
    """Print formatted test results."""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST RESULTS")
    print("=" * 60)
    
    successful_results = [r for r in results if r.get("success", False)]
    
    if not successful_results:
        print("No successful tests completed.")
        return
    
    # Sort by time (fastest first)
    successful_results.sort(key=lambda x: x["time"])
    
    print(f"{'System':<15} {'Time (s)':<12} {'Files':<8} {'Throughput':<12}")
    print("-" * 60)
    
    for result in successful_results:
        system = result["system"]
        time_taken = result["time"]
        files = result.get("files_processed", 0)
        throughput = files / time_taken if time_taken > 0 else 0
        
        print(f"{system:<15} {time_taken:<12.2f} {files:<8} {throughput:<12.2f} files/sec")
    
    # Calculate improvements
    if len(successful_results) >= 2:
        fastest = successful_results[0]
        slowest = successful_results[-1]
        
        if fastest["time"] > 0:
            improvement = slowest["time"] / fastest["time"]
            print(f"\nPerformance improvement: {improvement:.2f}x faster")
            print(f"Fastest system: {fastest['system']}")
            print(f"Slowest system: {slowest['system']}")


def main():
    """Run performance tests."""
    print("Video Labels Organizer - Performance Test")
    print("=" * 50)
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = os.path.join(temp_dir, "source")
        target_dir = os.path.join(temp_dir, "target")
        
        # Create test files
        print(f"Creating test files in {source_dir}...")
        test_files = create_test_files(source_dir, count=20)
        print(f"Created {len(test_files)} test files")
        
        results = []
        
        # Test old system
        if OLD_SYSTEM_AVAILABLE:
            old_result = test_old_system(source_dir, target_dir)
            results.append(old_result)
        
        # Test new sync system
        new_result = test_new_system(source_dir, target_dir)
        results.append(new_result)
        
        # Test new async system
        try:
            async_result = asyncio.run(test_async_system(source_dir, target_dir))
            results.append(async_result)
        except Exception as e:
            print(f"Async test failed: {e}")
        
        # Print results
        print_results(results)
        
        # Additional analysis
        print("\n" + "=" * 60)
        print("DETAILED ANALYSIS")
        print("=" * 60)
        
        for result in results:
            if result.get("success"):
                print(f"\n{result['system'].upper()} SYSTEM:")
                print(f"  Time: {result['time']:.2f} seconds")
                print(f"  Files processed: {result.get('files_processed', 0)}")
                
                if 'ffprobe_calls' in result:
                    print(f"  ffprobe calls: {result['ffprobe_calls']}")
                
                if 'errors' in result:
                    print(f"  Errors: {result['errors']}")
                
                throughput = result.get('files_processed', 0) / result['time']
                print(f"  Throughput: {throughput:.2f} files/sec")
            else:
                print(f"\n{result['system'].upper()} SYSTEM: FAILED")
                print(f"  Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 