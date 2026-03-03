# Week 1 Discovery Notes: USGS NSHMP Fortran Corpus

## Repository Overview

**Repository:** https://github.com/usgs/nshmp-haz-fortran
**Tag:** nshm2014r1
**Commit:** 9f78db0 (changed read me to markdown)

## Corpus Statistics

| Metric | Value |
|--------|-------|
| Total Fortran Files | 28 |
| Total Lines of Code | ~89,759 |
| Source Directory | `src/` |
| Utility Directory | `src/util/` |
| Scripts Directory | `scripts/` |

## File Inventory

### Main Source Files (`src/`)
| File | Size (lines) | Purpose |
|------|-------------|---------|
| hazFXnga13l.f | ~577,794 bytes | Hazard calculation with NGA relations (Western US) |
| hazFXnga13p.f | ~569,288 bytes | Hazard calculation with NGA relations |
| hazFXnga13z.f | ~569,930 bytes | Hazard calculation with NGA relations |
| hazgridXnga13l.f | ~554,171 bytes | Gridded hazard calculation |
| deaggFLTH.f | ~568,958 bytes | Deaggregation for fault sources |
| deaggGRID.f | ~591,886 bytes | Deaggregation for gridded sources |
| deaggSUBD.f | ~166,382 bytes | Deaggregation for subduction sources |
| hazSUBX.f | ~159,581 bytes | Subduction hazard calculation |
| sum_haz.f | ~43,386 bytes | Hazard curve summation |
| combine_cms.f | ~15,285 bytes | Combine CMS (Conditional Mean Spectrum) |
| hazallXL.v5.f | ~19,204 bytes | Hazard curve combination/utility |
| hazallXL.v4.f | ~17,524 bytes | Hazard curve combination/utility |
| hazallXL.v2.f | ~17,169 bytes | Hazard curve combination/utility |
| hazpoint.f | ~8,415 lines | Point hazard extraction |
| hazinterpnga.f | ~7,104 bytes | Interpolation utilities |

### Utility Files (`src/util/`)
- `assim.2013.f` - Assimilation utilities
- `avg_dist.f` - Average distance calculations
- `fltrate.2013.f` - Fault rate calculations
- `fltrate.v2.f` - Fault rate calculations (v2)
- `get_akprob.f` - Alaska probability
- `get_avalue.f` - A-value extraction
- `gethead.nga.f` - Header reading
- `getmeanrjf.f` - Mean rupture distance
- `gutenberg.f` - Gutenberg-Richter utilities
- `swapf.c` - Byte swapping (C)

## Fortran Patterns Observed

### 1. Fixed-Form Fortran 77/90 Style
All files use fixed-form Fortran with:
- Column 1: Comment indicator (`c` or `C`)
- Columns 1-5: Line numbers (rarely used)
- Column 6: Continuation character
- Columns 7-72: Statement code

```fortran
c--- This is a comment
      subroutine example()
      write(6,*)'Hello'
     +' world'     ! continuation with +
      end
```

### 2. Program Structure
- Single main program per file (no modules)
- Subroutines embedded within files
- Heavy use of `include` files for shared declarations

### 3. Naming Conventions
- Files named by function: `haz*.f` = hazard programs
- Version suffixes: `.v2`, `.v3`, `.v4`, `.v5`
- NGA suffix: `nga13` indicates 2013 NGA West-2 relationships

### 4. Ground Motion Prediction Equations (GMPEs)
The code implements multiple GMPEs:
- ASK13 (Abrahamson, Silva & Kamai 2013)
- CB13 (Campbell & Bozorgnia 2013)
- CY13 (Chiou & Youngs 2013)
- Idriss 2013
- BSSA 2013 (Boore et al.)
- Pezeshk 2011 (Central/Eastern US)
- Atkinson & Boore 2006

### 5. Data Structures
Uses Fortran 90 derived types:
```fortran
type header
  character*128 :: name(6)
  real*4 :: period
  integer*4 :: nlev
  real*4 :: xlev(20)
  real*4 :: extra(10)
end type header
```

### 6. File I/O
- Binary files with header records
- Direct access for large data sets
- Uses C utilities (`iosubs.c`) for low-level I/O

### 7. Memory Management
- Cray pointers for dynamic allocation
- `malloc` calls for array allocation
- Large arrays for gridded calculations

## Key Subroutines Identified

| Subroutine | Location | Purpose |
|------------|----------|---------|
| Main programs | Various | Top-level hazard calculation |
| ASK13 | hazFXnga13l.f | Abrahamson-Stafford-Kamai GMPE |
| CB13 | hazFXnga13l.f | Campbell-Bozorgnia GMPE |
| CY2013 | hazFXnga13l.f | Chiou-Youngs GMPE |
| getmeanrjf | getmeanrjf.f | Mean rupture distance calculation |

## Hazard Calculation Flow

1. **Input**: Source model (faults, grids), site parameters
2. **Distance Calculation**: Rupture-to-site distances
3. **GMPE Evaluation**: Ground motion at various periods
4. **Probability Integration**: Annual rate of exceedance
5. **Output**: Hazard curves (PGA, SA at various periods)

## Sample Queries for Testing

1. "Where is hazard computed?"
2. "What does subroutine CY201305_NGA do?"
3. "How are ground motion prediction equations called?"
4. "Where is the probability calculation performed?"
5. "What is the purpose of the hazgridX program?"
6. "How does the deaggregation work?"
7. "What is the relationship between magnitude and ground motion?"
8. "How are fault sources handled?"
9. "Where is Vs30 used in the calculations?"
10. "What is the main entry point for hazard calculation?"

## Observations for RAG System

### Strengths
- Well-commented code (extensive header comments)
- Clear file naming conventions
- Modular GMPE implementations
- Detailed version history in comments

### Challenges
- Large files (>500KB) require careful chunking
- Mixed Fortran 77/90 syntax
- Embedded subroutines within main programs
- Heavy reliance on external data files
- Comments may be domain-specific (seismology)

### Chunking Strategy
- Primary unit: Individual subroutines/functions
- Fallback: Fixed line windows for code not in subroutines
- Special handling: Long data/parameter blocks

## Next Steps

1. Run ingestion pipeline to populate database
2. Test retrieval with sample queries
3. Evaluate chunk quality and relevance
4. Iterate on chunking parameters if needed
