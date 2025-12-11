# Proposal: Async Disk Usage Display with Progress Indicator

## Problem Statement

Currently, `prime-uve list -v` blocks for ~1 second while calculating disk usage for all venvs before displaying anything. Users wait staring at a blank screen even though we could show project info immediately.

## Current Behavior

```
$ prime-uve list -v
[waits 1 second with no output...]
[shows complete table with all disk usage calculated]
```

## Proposed Behavior

```
$ prime-uve list -v
Managed Virtual Environments

STATUS  PROJECT                SIZE
[OK]    prime-uve              [calculating...]
[OK]    uv                     [calculating...]
...

[updates in-place as calculations complete]

STATUS  PROJECT                SIZE
[OK]    prime-uve              46.3 MB
[OK]    uv                     245.4 MB
...
```

## Design Approach

### Option 1: Progressive Update (Recommended)

Display table immediately with placeholders, calculate in background, update as results arrive.

**Pros**:
- Instant feedback (0.2s to show table)
- Feels responsive even if calculation takes time
- Can show progress (e.g., "Calculating... 3/8")

**Cons**:
- More complex implementation
- Terminal manipulation required (ANSI escape codes)

### Option 2: Spinner + Total Time

Show table with "Calculating..." spinner, then update all at once.

**Pros**:
- Simpler implementation
- Clear indication something is happening
- No partial state

**Cons**:
- Still blocks for full calculation time
- Less responsive feel

### Option 3: Parallel Calculation with ThreadPoolExecutor

Calculate disk usage for multiple venvs simultaneously.

**Pros**:
- Actually faster (2-4× with 4 workers)
- Works well with progressive updates

**Cons**:
- Thread overhead
- Potential I/O contention on slow drives

## Recommended Implementation: Option 1 + Option 3

Combine progressive display with parallel calculation for maximum responsiveness.

### Phase 1: Display Table Immediately

```python
def output_table(results: list, stats: dict, verbose: bool) -> None:
    """Output results with async disk usage calculation."""
    echo("Managed Virtual Environments\n")

    # Show legend
    click.secho(f"Legend: ...")

    if verbose:
        # Display table structure immediately
        for result in results:
            # Show project info without disk usage
            echo(f"{status_symbol} {project_name}")
            echo(f"  Project: {project_path}")
            echo(f"  Venv:    {venv_path_expanded}")
            echo(f"  Size:    [calculating...]")  # Placeholder
            echo("")

        # Now calculate and update
        update_disk_usage_async(results)
```

### Phase 2: Async Calculation with Progress

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

def update_disk_usage_async(results: list) -> None:
    """Calculate disk usage in parallel and update display."""
    total_venvs = len(results)
    completed = 0

    # Show progress line at bottom
    progress_line = len(results) * 4 + 5  # Approximate line count

    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all calculations
        future_to_result = {
            executor.submit(get_disk_usage, r.venv_path_expanded): (i, r)
            for i, r in enumerate(results)
            if r.venv_path_expanded.exists()
        }

        for future in as_completed(future_to_result):
            idx, result = future_to_result[future]
            completed += 1

            try:
                size = future.result()
                # Update specific line with ANSI escape codes
                move_cursor_to_line(idx * 4 + 7)  # Size line for this venv
                echo(f"  Size:    {format_bytes(size)}")

                # Update progress at bottom
                move_cursor_to_bottom()
                echo(f"\rCalculating disk usage... {completed}/{total_venvs}")
            except Exception:
                pass

        # Clear progress line
        move_cursor_to_bottom()
        echo("\r" + " " * 50 + "\r")
```

### Phase 3: Terminal Manipulation Helpers

```python
def move_cursor_to_line(line: int) -> None:
    """Move cursor to specific line using ANSI escape codes."""
    sys.stdout.write(f"\033[{line};0H")
    sys.stdout.flush()

def move_cursor_to_bottom() -> None:
    """Move cursor to bottom of terminal."""
    sys.stdout.write("\033[999;0H")  # Move far down
    sys.stdout.write("\033[1A")       # Up one line
    sys.stdout.flush()

def clear_line() -> None:
    """Clear current line."""
    sys.stdout.write("\033[2K")
    sys.stdout.flush()
```

## Alternative: Simpler Streaming Approach

For a simpler implementation that still provides instant feedback:

```python
def output_table_streaming(results: list, stats: dict, verbose: bool) -> None:
    """Stream results as we calculate them."""
    echo("Managed Virtual Environments\n")

    if verbose:
        # Calculate and display one at a time
        for result in results:
            # Show basic info immediately
            echo(f"{status_symbol} {project_name}")
            echo(f"  Project: {project_path}")
            echo(f"  Venv:    {venv_path_expanded}")

            # Calculate size for this venv only
            if result.venv_path_expanded.exists():
                size = get_disk_usage(result.venv_path_expanded)
                echo(f"  Size:    {format_bytes(size)}")
            else:
                echo(f"  Size:    0 B")
            echo("")

    # Summary at the end
    echo(f"\nSummary: {stats['total']} total...")
```

**Benefits**:
- Much simpler - no threading, no cursor manipulation
- Still provides instant feedback (first venv shows immediately)
- Progressive output feels responsive
- Total time same, but perceived performance better

**Drawback**:
- Not truly parallel, still serial calculation
- Each venv waits for previous to complete

## Recommended Path

**Start with Streaming Approach** (simpler):
1. Display and calculate one venv at a time
2. User sees output immediately (first venv in ~0.2s)
3. Perceived performance is much better even if total time is same

**Later: Add Parallel Calculation** (if needed):
1. Add ThreadPoolExecutor for true speedup
2. Calculate all venvs in parallel
3. Display results as they complete

## Implementation Effort

**Streaming approach**: 1-2 hours
- Modify `output_table()` in list.py
- Move disk usage calculation into display loop
- Update tests (minimal changes)

**Parallel + cursor manipulation**: 3-4 hours
- Implement ANSI escape code helpers
- Add ThreadPoolExecutor logic
- Handle edge cases (non-TTY, narrow terminals)
- More complex testing

## User Experience Comparison

### Current (blocking):
```
$ prime-uve list -v
[blank for 1 second]
[full table appears]
```
**Feels slow** even though it's only 1 second.

### Streaming:
```
$ prime-uve list -v
Managed Virtual Environments

prime-uve            [OK]  Valid     46.3 MB
[next venv appears 0.15s later]
uv                   [OK]  Valid     245.4 MB
[continues streaming...]
```
**Feels instant** because output starts immediately.

### Parallel + updates:
```
$ prime-uve list -v
Managed Virtual Environments

prime-uve            [OK]  Valid     [calculating...]
uv                   [OK]  Valid     [calculating...]
...
[all appear instantly]
[sizes update in 0.3s as calculations complete in parallel]
```
**Feels fastest** but more complex.

## Decision

**Recommend: Streaming approach**
- Simplest to implement
- Biggest perceived performance improvement
- No threading complexity
- Works in all terminals (no ANSI required)

Can be enhanced later with parallel calculation if needed.

## Breaking Changes

None - this only affects display timing, not output format.

## Testing

1. **Unit tests**: Test streaming display logic
2. **Integration tests**: Verify all venvs displayed
3. **Performance tests**: Measure time-to-first-output (<0.3s)
4. **Manual tests**: Verify output looks correct across terminals
