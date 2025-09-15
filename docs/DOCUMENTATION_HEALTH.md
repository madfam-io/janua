# 📊 Documentation Health Dashboard

> Auto-generated health metrics for Plinto documentation
> Last updated: 9/14/2025, 4:55:31 PM

## 🏥 Overall Health Score: 60/100 🟠

`[████████████░░░░░░░░]`

## 📈 Key Metrics

### Structure Overview
| Metric | Value | Status |
|--------|-------|--------|
| Internal Documentation | 90 files | ✅ |
| Public Documentation | 29 files | ✅ |
| Pending Drafts | 0 files | ✅ |
| Archived Content | 5 files | ℹ️ |
| Total Size | 1.4G | ℹ️ |

### Content Quality
| Metric | Value | Status |
|--------|-------|--------|
| TODO/FIXME in Public | 0 | ✅ |
| Code Examples | 0 blocks | ⚠️ |
| Images | 18 | ℹ️ |
| Internal Links | 779 | ℹ️ |

### Risk Assessment
| Risk Factor | Level | Action Required |
|-------------|-------|-----------------|
| Large Files | ⚠️ 11 files | Consider splitting |
| Old Drafts | ✅ None | None |
| Duplicate Content | High | Immediate review |
| Sensitive Information | High | Security review |

### Documentation Coverage
| Area | Status | Completeness |
|------|--------|--------------|
| API Documentation | ✅ Present | Complete |
| SDK Documentation | ✅ Present | Complete |
| User Guides | ✅ Present | Complete |
| Quick Start | ❌ Missing | Required |

## 🚨 Active Issues

- ⚠️ 11 large files detected (>100KB)

## 📋 Recommended Actions

4. **Remove duplicate content** - Consolidate documentation to single location
5. **Add quick start guide** - Help users get started quickly

## 🔄 Automation Status

| Check | Status | Schedule |
|-------|--------|----------|
| Pre-commit Hooks | ✅ Configured | Every commit |
| CI/CD Validation | ✅ Configured | Every PR |
| Health Dashboard | ✅ Generated | Weekly |

## 📊 Trend Analysis

```
Documentation Growth (Last 30 days)
Internal: → Stable
Public:   → Stable
Quality:  → Stable
```

## 🛠️ Quick Commands

```bash
# Run full validation
./scripts/docs-pipeline.sh health

# Check for duplicates
./scripts/docs-pipeline.sh check

# Validate specific file
./scripts/docs-pipeline.sh validate <file>

# Promote draft to public
./scripts/docs-pipeline.sh promote <draft> <target>
```

---

*This dashboard is automatically generated. To update, run: `node scripts/generate-docs-dashboard.js`*

*For detailed guidelines, see: [Content Guidelines](./CONTENT_GUIDELINES.md)*