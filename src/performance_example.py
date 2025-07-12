"""
Example usage and integration for PerformantMediaOrganiser.

This module demonstrates how to use the new concurrent media organizer
with performance monitoring, error handling, and integration examples.
"""

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional

from .performant_media_organiser import (
    PerformantMediaOrganiser,
    organize_files_async,
    organize_files_sync
)
from .logger import logging


def progress_callback(percent: int) -> None:
    """Example progress callback function."""
    print(f"Progress: {percent}%")


async def example_async_usage():
    """Example of async usage with performance monitoring."""
    print("=== Async Performance Example ===")
    
    # Initialize with custom settings
    async with PerformantMediaOrganiser(
        max_workers=16,
        batch_size=25,
        timeout_seconds=30,
        memory_limit_mb=256
    ) as organizer:
        
        start_time = time.time()
        
        # Process files
        results = await organizer.organize_files(
            source="C:/Videos/Source",
            target="C:/Videos/Organized",
            dry_run=True,
            progress_callback=progress_callback
        )
        
        # Performance analysis
        stats = organizer.get_performance_stats()
        total_time = time.time() - start_time
        
        print(f"\nPerformance Results:")
        print(f"  Files processed: {stats['files_processed']}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  ffprobe calls: {stats['ffprobe_calls']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Throughput: {stats['files_processed'] / total_time:.2f} files/sec")
        
        # Show results summary
        successful = sum(1 for r in results if not r.skipped and not r.error)
        errors = sum(1 for r in results if r.error)
        skipped = sum(1 for r in results if r.skipped)
        
        print(f"\nResults Summary:")
        print(f"  Successful: {successful}")
        print(f"  Errors: {errors}")
        print(f"  Skipped: {skipped}")


def example_sync_usage():
    """Example of synchronous usage."""
    print("=== Sync Performance Example ===")
    
    start_time = time.time()
    
    # Use the sync wrapper
    results = organize_files_sync(
        source="C:/Videos/Source",
        target="C:/Videos/Organized",
        dry_run=True,
        progress_callback=progress_callback,
        max_workers=16
    )
    
    total_time = time.time() - start_time
    
    print(f"\nSync Performance Results:")
    if results is not None:
        print(f"  Files processed: {len(results)}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {len(results) / total_time:.2f} files/sec")
    else:
        print(f"  Files processed: 0")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: 0 files/sec")


def example_batch_processing():
    """Example of batch processing with memory management."""
    print("=== Batch Processing Example ===")
    
    async def process_in_batches():
        async with PerformantMediaOrganiser(
            batch_size=10,  # Small batches for memory efficiency
            memory_limit_mb=128
        ) as organizer:
            
            # Process multiple directories
            directories = [
                "C:/Videos/Source1",
                "C:/Videos/Source2",
                "C:/Videos/Source3"
            ]
            
            all_results = []
            
            for i, source_dir in enumerate(directories):
                print(f"Processing directory {i+1}/{len(directories)}: {source_dir}")
                
                results = await organizer.organize_files(
                    source=source_dir,
                    target="C:/Videos/Organized",
                    dry_run=True
                )
                
                all_results.extend(results)
                
                # Reset stats between batches to monitor each directory
                organizer.reset_stats()
            
            return all_results
    
    # Run the batch processing
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(process_in_batches())
        
        print(f"\nBatch Processing Complete:")
        print(f"  Total files processed: {len(results)}")
        
    finally:
        loop.close()


def example_error_handling():
    """Example of comprehensive error handling."""
    print("=== Error Handling Example ===")
    
    async def robust_processing():
        async with PerformantMediaOrganiser(
            timeout_seconds=10,  # Shorter timeout for testing
            max_workers=4
        ) as organizer:
            
            try:
                results = await organizer.organize_files(
                    source="C:/Videos/Source",
                    target="C:/Videos/Organized",
                    dry_run=True
                )
                
                # Analyze errors
                errors = [r for r in results if r.error]
                successful = [r for r in results if not r.error and not r.skipped]
                
                print(f"Processing completed:")
                print(f"  Successful: {len(successful)}")
                print(f"  Errors: {len(errors)}")
                
                # Show error details
                if errors:
                    print("\nError details:")
                    for result in errors[:5]:  # Show first 5 errors
                        print(f"  {result.original_path}: {result.error}")
                
                return results
                
            except Exception as e:
                print(f"Critical error: {e}")
                return []
    
    # Run with error handling
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(robust_processing())
        
    finally:
        loop.close()


def example_integration_with_existing():
    """Example of integrating with existing codebase."""
    print("=== Integration Example ===")
    
    # Simulate existing code that uses the old interface
    def legacy_organize_files(source: str, target: str, dry_run: bool = True):
        """Legacy function that uses the old interface."""
        from .media_organiser import organize_files as old_organize_files
        
        if dry_run:
            # Use new performant version for dry run
            return organize_files_sync(source, target, dry_run=True)
        else:
            # Use old version for actual file operations (for safety)
            return old_organize_files(source, target, dry_run=False)
    
    # Test the integration
    try:
        results = legacy_organize_files(
            source="C:/Videos/Source",
            target="C:/Videos/Organized",
            dry_run=True
        )
        
        if results is not None:
            print(f"Integration test completed: {len(results)} files processed")
        else:
            print("Integration test completed: No results")
        
    except Exception as e:
        print(f"Integration error: {e}")


def performance_comparison():
    """Compare performance between old and new implementations."""
    print("=== Performance Comparison ===")
    
    async def compare_performance():
        source = "C:/Videos/Source"
        target = "C:/Videos/Organized"
        
        # Test new implementation
        print("Testing new performant implementation...")
        start_time = time.time()
        
        async with PerformantMediaOrganiser(max_workers=16) as organizer:
            new_results = await organizer.organize_files(
                source, target, dry_run=True
            )
        
        new_time = time.time() - start_time
        new_stats = organizer.get_performance_stats()
        
        print(f"New implementation:")
        print(f"  Time: {new_time:.2f}s")
        if new_results is not None:
            print(f"  Files: {len(new_results)}")
        else:
            print(f"  Files: 0")
        print(f"  ffprobe calls: {new_stats['ffprobe_calls']}")
        
        # Test old implementation (if available)
        try:
            from .media_organiser import organize_files as old_organize_files
            
            print("\nTesting old implementation...")
            start_time = time.time()
            
            old_results = old_organize_files(source, target, dry_run=True)
            
            old_time = time.time() - start_time
            
            print(f"Old implementation:")
            print(f"  Time: {old_time:.2f}s")
            print(f"  Files: {len(old_results)}")
            
            # Calculate improvement
            if old_time > 0:
                improvement = old_time / new_time
                print(f"\nPerformance improvement: {improvement:.2f}x faster")
            
        except ImportError:
            print("Old implementation not available for comparison")
    
    # Run comparison
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(compare_performance())
        
    finally:
        loop.close()


if __name__ == "__main__":
    """Run all examples."""
    print("PerformantMediaOrganiser Examples")
    print("=" * 40)
    
    # Run examples
    example_async_usage()
    print("\n" + "=" * 40)
    
    example_sync_usage()
    print("\n" + "=" * 40)
    
    example_batch_processing()
    print("\n" + "=" * 40)
    
    example_error_handling()
    print("\n" + "=" * 40)
    
    example_integration_with_existing()
    print("\n" + "=" * 40)
    
    performance_comparison()
    print("\n" + "=" * 40)
    
    print("All examples completed!") 