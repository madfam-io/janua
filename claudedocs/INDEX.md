# Claude Internal Documentation Index

**Purpose**: Internal documentation for Claude Code sessions, implementation progress, and technical analysis.  
**Audience**: Development team, future Claude sessions  
**Last Updated**: November 17, 2025

## Directory Structure

```
claudedocs/
├── session-notes/             # Session summaries and breakthroughs
├── guides/                    # Implementation guides and foundations
└── INDEX.md                   # This file
```

**Note**: Implementation reports have been consolidated in `docs/implementation-reports/` for better organization and discoverability.

## Navigation

### 📝 Session Notes

**Recent Sessions**:
- [2025-11-13 Breakthrough Final](session-notes/2025-11-13-breakthrough-final.md) - Major testing breakthrough session
- [2025-11-13 Auth Endpoints](session-notes/2025-11-13-auth-endpoints.md) - Auth endpoint implementation session

### 📖 Guides

**Foundation**:
- [Week 1 Foundation Complete](guides/week1-foundation-complete.md) - Week 1 milestone completion
- [Week 1 Implementation Guide](guides/week1-implementation-guide.md) - Week 1 implementation details

## Related Documentation

**For comprehensive implementation reports, see**: [`docs/implementation-reports/`](../docs/implementation-reports/)

Key recent reports:
- [Backup Codes Test Suite Completion](../docs/implementation-reports/backup-codes-test-suite-completion.md) - Complete test suite with 100% passing
- [Week 6 Documentation](../docs/implementation-reports/) - All Week 6 implementation reports
- [Week 5 Final Summary](../docs/implementation-reports/week5-final-summary.md) - Week 5 completion

## Document Lifecycle

### Status Indicators

- **[CURRENT]** - Active, up-to-date documentation
- **[ARCHIVED]** - Historical, superseded by newer documents
- **[DRAFT]** - Work in progress, not finalized

### Naming Convention

All documents follow the pattern: `YYYY-MM-DD-descriptive-name.md` or `descriptive-name.md` for timeless guides.

### When to Archive

Documents should be moved to `archive/` when:
- Superseded by a newer, more comprehensive document
- Implementation phase is complete and historical reference only
- Content is outdated but valuable for context
- Age > 6 months and no longer actively referenced

## Usage Guidelines

### For Development Team

1. **Before starting work**: Check recent session notes and implementation reports
2. **After completing work**: Create session note or implementation report
3. **Monthly review**: Archive superseded documents, update this index

### For Future Claude Sessions

1. **Session start**: Read this INDEX and recent session notes
2. **Reference**: Use audits and implementation reports for context
3. **Session end**: Create session note with summary and outcomes
4. **Major milestones**: Update relevant reports or create new ones

## Related Documentation

- [Developer Documentation](../docs/README.md) - Public-facing documentation
- [Version Guide](../VERSION_GUIDE.md) - Package versioning information
- [Documentation System](../docs/DOCUMENTATION_SYSTEM.md) - Documentation infrastructure

## Maintenance

**Review Schedule**:
- Weekly: Update INDEX with new documents
- Monthly: Review and archive superseded content
- Quarterly: Comprehensive audit and cleanup

**Last Review**: November 17, 2025  
**Next Review**: December 17, 2025

## Recent Cleanup (November 17, 2025)

**Removed obsolete files**:
- Superseded Week 5 loose files (consolidated into structured reports)
- Obsolete implementation reports (superseded by newer comprehensive docs)
- Temporary debug logs and backup files
- Empty directories

**Result**: Cleaner structure with all implementation reports now in `docs/implementation-reports/` for better discoverability.
