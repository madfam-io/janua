# Sprint Quality Checklist Template

**Purpose**: Prevent critical bugs through systematic pre-testing validation  
**When to Use**: Before starting comprehensive testing in any sprint  
**Time Required**: 1-2 hours for critical modules, 30 minutes for minor changes

---

## 📋 Pre-Testing Foundation Checklist

### 1. Model-Service Alignment ✅

**Goal**: Prevent AttributeError bugs from missing model fields

**Steps**:
```bash
# Scan services for field references
grep -r "\\.status\|\\.state\|\\.active\|\\.enabled" app/services/*.py

# Cross-reference with model definitions
grep "class.*Base" app/models/*.py -A 30 | grep "status\|state\|active"

# Verify all referenced fields exist in models
```

**Critical Check**:
- [ ] All service field writes (`obj.field = value`) have corresponding model fields
- [ ] All service field reads (`obj.field == value`) reference existing fields
- [ ] Enum values in services match enum definitions in models

**Red Flags**:
- ⚠️ Service writes to `status` but model has `implementation_status`
- ⚠️ Service checks `active` but model has `is_active`
- ⚠️ Enum value mismatch (service uses `COMPLIANT`, enum has `EFFECTIVE`)

**Example Issues Found**:
- Week 4: `OrganizationMember.status` missing (10 test failures)
- Week 4.5: `ComplianceControl.status` missing (would crash in production)

---

### 2. Database Migration Verification ✅

**Goal**: Ensure all model changes have corresponding migrations

**Steps**:
```bash
# Check for recent model changes
git diff HEAD~5 app/models/

# List recent migrations
ls -lt alembic/versions/ | head -5

# Verify migration exists for each model change
alembic history | head -10
```

**Critical Check**:
- [ ] Every new Column() has a migration
- [ ] Every dropped field has a downgrade path
- [ ] Default values are set for new non-nullable columns
- [ ] Indexes created for commonly filtered fields

**Red Flags**:
- ⚠️ Model has new field but no migration in last 7 days
- ⚠️ Migration adds non-nullable column without default
- ⚠️ No composite index for common query patterns

**Migration Best Practices**:
- Always add default values for new non-nullable columns
- Create indexes for status/active/enabled fields
- Add composite indexes for common WHERE clause patterns
- Include meaningful revision comments

---

### 3. Integration Smoke Tests ✅

**Goal**: Verify basic CRUD operations work before comprehensive testing

**Steps**:
```bash
# Run minimal integration tests
pytest tests/integration/test_smoke.py -v

# Or create quick smoke test:
pytest tests/integration/ -m smoke --tb=short
```

**Critical Check**:
- [ ] Can create records in all critical tables
- [ ] Can read records with common query patterns
- [ ] Can update records including status changes
- [ ] Can delete/soft-delete records

**Red Flags**:
- ⚠️ IntegrityError on foreign key constraints
- ⚠️ OperationalError from missing columns
- ⚠️ AttributeError from model-service misalignment

---

### 4. Enum Value Validation ✅

**Goal**: Ensure service code and model enums are synchronized

**Steps**:
```bash
# Find all enum definitions
grep "class.*Enum" app/models/*.py

# Find all enum usage in services
grep "Status\\." app/services/*.py | grep -v "import"

# Cross-reference values
```

**Critical Check**:
- [ ] All enum values used in services exist in enum definitions
- [ ] Enum imports are correct (from right module)
- [ ] Default enum values are valid choices

**Red Flags**:
- ⚠️ `ControlStatus.COMPLIANT` used but enum only has `EFFECTIVE`
- ⚠️ Default value not in enum choices
- ⚠️ String comparison instead of enum comparison

---

## 🧪 Testing Coverage Prerequisites

### 5. Test Environment Setup ✅

**Goal**: Ensure test infrastructure is ready

**Steps**:
```bash
# Check test database connection
pytest tests/ --collect-only

# Verify fixtures work
pytest tests/conftest.py -v

# Check mocking setup
pytest tests/unit/ -k "test_*" --tb=short -x
```

**Critical Check**:
- [ ] Database fixtures create/teardown properly
- [ ] AsyncMock available for async operations
- [ ] Redis mock configured (if needed)
- [ ] Authentication mocks work

**Red Flags**:
- ⚠️ Database connection errors
- ⚠️ Fixture scope issues (session vs function)
- ⚠️ Missing pytest plugins

---

### 6. Test Data Consistency ✅

**Goal**: Verify test data matches model constraints

**Steps**:
```python
# Check factory/fixture data
cat tests/factories/*.py | grep "status\|active\|enabled"

# Ensure test data uses valid enum values
grep "Status\\." tests/fixtures/*.py
```

**Critical Check**:
- [ ] Factory data uses valid enum values
- [ ] Required fields have values in factories
- [ ] Foreign keys reference valid test data
- [ ] Dates/timestamps are realistic

**Red Flags**:
- ⚠️ Factory uses string instead of enum
- ⚠️ Missing required fields in test data
- ⚠️ Invalid foreign key references

---

## 🔍 Code Quality Gates

### 7. TODO Resolution Strategy ✅

**Goal**: Categorize and plan TODO resolution

**Steps**:
```bash
# Count TODOs
grep -rn "TODO\|FIXME\|XXX" app/ --include="*.py" --exclude-dir=tests | wc -l

# Categorize by severity
grep -rn "TODO" app/ --include="*.py" --exclude-dir=tests
```

**Critical Check**:
- [ ] Zero CRITICAL TODOs (blocking functionality)
- [ ] IMPORTANT TODOs have tickets/plan
- [ ] NICE-TO-HAVE TODOs in backlog
- [ ] FALSE POSITIVES identified

**Categorization**:
- **🔴 CRITICAL**: Blocks core functionality or security
- **🟡 IMPORTANT**: Needed for production but not blocking
- **🟢 NICE-TO-HAVE**: Future enhancements, defer to backlog

---

### 8. Import and Dependency Check ✅

**Goal**: Verify all imports resolve correctly

**Steps**:
```bash
# Check for circular imports
python -m app.main

# Verify critical imports
python -c "from app.services.billing_service import BillingService"
python -c "from app.models.compliance import ComplianceControl"
```

**Critical Check**:
- [ ] No circular import errors
- [ ] All model imports work
- [ ] All service imports work
- [ ] Enum imports resolve

**Red Flags**:
- ⚠️ ImportError or ModuleNotFoundError
- ⚠️ Circular dependency warnings
- ⚠️ Missing __init__.py files

---

## 📊 Coverage Baseline Validation

### 9. Coverage Gap Analysis ✅

**Goal**: Identify untested critical paths before adding tests

**Steps**:
```bash
# Generate baseline coverage
pytest tests/ --cov=app --cov-report=term-missing

# Identify 0% coverage modules
pytest tests/ --cov=app --cov-report=json
cat coverage.json | jq '.files | to_entries[] | select(.value.summary.percent_covered < 10)'
```

**Critical Check**:
- [ ] Baseline coverage documented
- [ ] Zero-coverage modules identified
- [ ] Critical modules (auth, payment, RBAC) have >0% coverage
- [ ] Coverage gaps explained

**Priority Modules** (Must Have >50% Coverage):
- Authentication services
- Payment/billing services  
- RBAC/authorization
- Compliance/audit logging
- Session management

---

### 10. Test Execution Baseline ✅

**Goal**: Establish passing test baseline before adding new tests

**Steps**:
```bash
# Run existing tests
pytest tests/ --tb=short -q

# Document failures
pytest tests/ --tb=short -q | tee baseline_failures.txt

# Categorize failures
```

**Critical Check**:
- [ ] Document current pass rate
- [ ] Categorize existing failures
- [ ] Identify blocking vs non-blocking failures
- [ ] Plan for fixing critical failures first

**Failure Categories**:
- **Blocking**: Prevent new tests from running
- **Related**: Same root cause as current work
- **Unrelated**: Can be deferred

---

## ✅ Final Validation

### Sprint Readiness Checklist

Before starting comprehensive testing, verify:

**Foundation** (MUST PASS):
- [ ] ✅ Model-service alignment verified
- [ ] ✅ Database migrations created
- [ ] ✅ Integration smoke tests pass
- [ ] ✅ Enum values validated

**Quality** (SHOULD PASS):
- [ ] ✅ Zero CRITICAL TODOs
- [ ] ✅ All imports resolve
- [ ] ✅ Test environment works
- [ ] ✅ Test data valid

**Metrics** (DOCUMENTED):
- [ ] ✅ Baseline coverage recorded
- [ ] ✅ Existing failures categorized
- [ ] ✅ Sprint goals defined

---

## 🎯 Sprint-Specific Adjustments

### Payment/Billing Sprint
Additional checks:
- [ ] Stripe/Conekta/Polar API mocks configured
- [ ] Webhook signature validation tested
- [ ] Currency handling verified
- [ ] Subscription status enum aligned

### Compliance Sprint
Additional checks:
- [ ] GDPR/SOC2 model fields complete
- [ ] Audit log hash chain working
- [ ] Consent status enum aligned
- [ ] Data export formats validated

### SSO/SCIM Sprint
Additional checks:
- [ ] SAML metadata generation works
- [ ] OIDC discovery endpoint responds
- [ ] SCIM schema matches models
- [ ] Certificate management functional

---

## 📈 Success Metrics

**Checkpoint Effectiveness**:
- Time invested: 1-2 hours
- Bugs prevented: 1-3 critical issues
- Test efficiency: 20-30% faster sprint
- Confidence level: HIGH before testing

**ROI Calculation**:
- Checkpoint time: 1-2 hours
- Debugging time saved: 4-8 hours
- Production bugs prevented: 1-2
- **ROI: 4-8x return**

---

## 🔄 Continuous Improvement

After each sprint, update this checklist with:
- New bug patterns discovered
- Additional validation steps
- Improved automation opportunities
- Lessons learned

**Version History**:
- v1.0 (2025-11-18): Initial template based on Week 4/4.5 findings
- Future: Add automation scripts, CI/CD integration

---

*Template created from Week 4 Security Sprint and Week 4.5 Stability Checkpoint lessons*  
*Prevents: AttributeError bugs, missing migrations, enum mismatches*  
*Estimated time savings: 4-8 hours per sprint*
