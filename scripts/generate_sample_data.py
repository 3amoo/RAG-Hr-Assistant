#!/usr/bin/env python3
"""Generate clearly synthetic HR policy documents for local evaluation.

The generated files are intentionally ignored by git. They are for testing the
upload, chunking, indexing and answering flow only; none of this is real policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path


DOCUMENTS = {
    "employee_handbook.txt": """Document: Employee Handbook
Department: People Operations
Effective date: 2026-01-15
Language: English

Welcome to the employee handbook. Normal working hours are 09:00 to 17:00,
Monday to Friday. Employees are expected to act professionally, respect
colleagues and follow company policies.

All employees must complete security awareness training during their first
month. Managers are responsible for outlining goals and providing regular
feedback. Changes to employment terms must be confirmed in writing.

Questions about this handbook should be sent to the People Operations team.
""",
    "leave_policy.txt": """Document: Annual Leave Policy
Department: People Operations
Effective date: 2026-02-01
Language: English

Full-time employees are entitled to 25 days of paid annual leave per calendar
year. Part-time employees accrue leave in proportion to their contracted hours.

Leave requests must be submitted at least two weeks in advance through the
internal portal. Managers should respond within five working days. Up to five
unused days may be carried into the following year; any additional unused days
are forfeited.

Sick leave is separate from annual leave and requires notification on the first
day of absence. Public holidays are not counted against annual leave.
""",
    "parental_leave_policy.txt": """Document: Parental Leave Policy
Department: People Operations
Effective date: 2026-03-01
Language: English

Employees are entitled to 16 weeks of paid parental leave following the birth
or adoption of a child. The first four weeks are available to either parent.
The remaining twelve weeks are available to the primary caregiver.

Leave must be requested at least eight weeks before the expected date where
possible. Employees must provide a birth certificate or adoption paperwork.
Parental leave does not reduce annual leave entitlement.

Employees returning from parental leave may request a phased return for up to
four weeks. Requests should be agreed with the manager and People Operations.
""",
    "remote_work_policy.txt": """Document: Remote Work Policy
Department: People Operations
Effective date: 2026-01-20
Language: English

Employees may work remotely up to three days per week after completing their
probation period. Remote work requires approval from the employee's manager.

Employees must have a reliable internet connection, a suitable workspace and
must keep company data on approved devices only. Video conferencing is expected
for team meetings. Core collaboration hours are 10:00 to 15:00 local time.

Remote work arrangements are reviewed every six months. Managers may withdraw
approval where performance or security requirements are not met.
""",
    "expense_policy.txt": """Document: Travel and Expense Policy
Department: Finance
Effective date: 2026-02-10
Language: English

Employees may claim reasonable expenses incurred for approved business travel.
Claims must be submitted within 30 days with a receipt. Meals are reimbursed up
to 30 currency units per day when travelling overnight.

Economy class travel is the default for flights under six hours. Any upgrade
must be approved in advance by a manager. Transport between airports and
accommodation is reimbursable.

Expenses that are not supported by a receipt will not be reimbursed. Questions
about this policy should be directed to the Finance team.
""",
    "code_of_conduct.txt": """Document: Code of Conduct
Department: People Operations
Effective date: 2026-01-05
Language: English

All employees must treat colleagues, customers and partners with respect.
Discrimination, harassment and intimidation are not tolerated.

Conflicts of interest must be disclosed to a manager. Gifts of significant
value may not be accepted from suppliers. Company confidential information
must not be shared outside approved channels.

Concerns may be reported to a manager or to the ethics mailbox. Reports are
handled confidentially and retaliation is prohibited.
""",
    "security_policy.txt": """Document: Information Security Policy
Department: Security
Effective date: 2026-04-01
Language: English

Passwords must be at least twelve characters and unique to each account.
Multi-factor authentication is required for all company systems.

Company laptops must use full-disk encryption and be locked when unattended.
Suspected phishing emails must be reported to the Security team immediately.
Do not install unapproved software on company devices.

Security incidents must be reported within 24 hours of discovery. Data must be
stored only in approved systems and shared only with authorised recipients.
""",
    "parental_leave_policy_ar.txt": """المستند: سياسة الإجازة الوالدية
القسم: عمليات الأفراد
تاريخ النفاذ: 2026-03-01
اللغة: العربية

يحق للموظفين الحصول على ستة عشر أسبوعاً من الإجازة الوالدية المدفوعة بعد
الولادة أو التبني. تُتاح الأسابيع الأربعة الأولى لأي من الوالدين، وتُتاح
الأسابيع الاثنا عشر المتبقية لمقدم الرعاية الأساسي.

يجب تقديم طلب الإجازة قبل ثمانية أسابيع من التاريخ المتوقع عند الإمكان.
يجب تقديم شهادة ميلاد أو مستندات التبني. لا تؤثر الإجازة الوالدية على رصيد
الإجازة السنوية.

يجوز للموظف العائد من الإجازة الوالدية طلب العودة التدريجية لمدة تصل إلى
أربعة أسابيع، بعد موافقة المدير وعمليات الأفراد.
""",
}


def generate(output_dir: Path, force: bool = False) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for name, content in DOCUMENTS.items():
        path = output_dir / name
        if path.exists() and not force:
            raise FileExistsError(
                f"{path} already exists. Use --force to overwrite generated files."
            )
        path.write_text(content.strip() + "\n", encoding="utf-8")
        written.append(path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/sample-data/policies"),
        help="Directory to write the generated documents into.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite files that already exist in the output directory.",
    )
    args = parser.parse_args()

    files = generate(args.output, force=args.force)
    print(f"Generated {len(files)} synthetic policy documents in {args.output}:")
    for path in files:
        print(f"  - {path.name}")


if __name__ == "__main__":
    main()
