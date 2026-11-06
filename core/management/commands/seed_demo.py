"""
Seed realistic demo data for FixIt Local (Fix Your Elaka).

Usage (after `python manage.py migrate`):
    python manage.py seed_demo            # create demo data
    python manage.py seed_demo --reset    # wipe previous demo data, then recreate

Creates: the admin account, 5 areas, 5 approved authorities (+1 pending),
6 citizens, ~16 reports in every workflow state with before/after photos,
verification records, status history, comments and votes.

Photos: put your own images in a `demo_photos/` folder next to manage.py, named
before_01.jpg ... before_16.jpg (and optionally after_01.jpg ...). The number is
the report's position in the REPORTS list below. Any photo that is missing is
generated automatically with Pillow, so the command always works.
"""
import io
import random
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import AuthorityProfile
from core.models import Area, Category
from interactions.models import Comment, Vote
from reports.models import Report, ReportStatusHistory, Verification

User = get_user_model()

DEMO_PASSWORD = "Demo@12345"

# ----------------------------------------------------------------------------
# Demo content
# ----------------------------------------------------------------------------
AREAS = {
    # name: (lat, lng)
    "Dhanmondi": (23.7461, 90.3742),
    "Mirpur": (23.8042, 90.3667),
    "Uttara": (23.8759, 90.3795),
    "Mohammadpur": (23.7662, 90.3589),
    "Gulshan": (23.7925, 90.4078),
}

CITIZENS = [
    # username, first, last
    ("citizen1", "Rafiq", "Ahmed"),
    ("citizen2", "Nusrat", "Jahan"),
    ("citizen3", "Tanvir", "Hasan"),
    ("citizen4", "Sadia", "Islam"),
    ("citizen5", "Imran", "Hossain"),
    ("citizen6", "Mim", "Akter"),
]

AUTHORITIES = [
    # username, first, last, department, area
    ("auth_dhanmondi", "Kamal", "Uddin", "Road & Infrastructure Dept.", "Dhanmondi"),
    ("auth_mirpur", "Farhana", "Rahman", "Waste Management Dept.", "Mirpur"),
    ("auth_uttara", "Shahed", "Karim", "WASA - Water & Drainage", "Uttara"),
    ("auth_mohammadpur", "Nazia", "Sultana", "Streetlight & Electricity Dept.", "Mohammadpur"),
    ("auth_gulshan", "Arif", "Chowdhury", "Public Safety Unit", "Gulshan"),
]
# Registered but NOT yet approved -> lets you demo the admin approval flow.
PENDING_AUTHORITY = ("auth_pending", "Rubel", "Mia", "Road & Infrastructure Dept.", "Mirpur")

# Report states
PENDING, REJECTED, VERIFIED = "pending", "rejected", "verified"
IN_PROGRESS, PROBLEM_FIXED, RESOLVED, CLOSED = (
    "in_progress", "problem_fixed", "resolved", "closed",
)

# (title, description, category, area, location_text, reporter_idx, state, days_ago)
REPORTS = [
    ("Large pothole near Dhanmondi Lake",
     "A deep pothole has formed on the road and two-wheelers keep skidding. It gets worse every time it rains.",
     "Road Damage", "Dhanmondi", "Road 8A, near Dhanmondi Lake", 0, RESOLVED, 20),
    ("Cracked footpath outside school",
     "Footpath tiles are broken and uneven right outside the school gate. Children and elderly people are at risk of tripping.",
     "Broken Footpath", "Dhanmondi", "Satmasjid Road, near the school gate", 1, PROBLEM_FIXED, 9),
    ("Streetlight not working",
     "The streetlight beside the park has been off for over a week. The lane is completely dark at night.",
     "Streetlight Problem", "Dhanmondi", "Road 27, beside the park", 2, IN_PROGRESS, 6),

    ("Garbage pile near the market",
     "Garbage has not been collected for days and the smell is spreading to nearby shops and homes.",
     "Garbage and Waste", "Mirpur", "Mirpur 10, near the kacha bazar", 3, RESOLVED, 18),
    ("Overflowing waste bin at bus stand",
     "The public bin is overflowing onto the road and attracting stray animals.",
     "Garbage and Waste", "Mirpur", "Mirpur 11 bus stand", 4, IN_PROGRESS, 5),
    ("Smoke from burning waste",
     "Waste is being burned in an empty plot every evening, causing heavy smoke across the neighbourhood.",
     "Air Pollution", "Mirpur", "Mirpur 12, block C empty plot", 5, VERIFIED, 3),

    ("Waterlogging after every rain",
     "Water stays on the road for hours after rain because the drain is blocked. Cars and rickshaws get stuck.",
     "Drainage and Waterlogging", "Uttara", "Sector 7, Road 12", 0, RESOLVED, 25),
    ("Very low water pressure",
     "Households in this block receive almost no water in the morning. The problem has continued for two weeks.",
     "Water Supply Problem", "Uttara", "Sector 4 residential area", 1, IN_PROGRESS, 7),
    ("Broken manhole cover on main road",
     "The manhole cover is broken and the open hole is a serious danger to vehicles and pedestrians.",
     "Safety Concern", "Uttara", "Sector 10 main road", 2, CLOSED, 14),
    ("Missing streetlight pole",
     "A streetlight pole was removed during road work and never replaced.",
     "Streetlight Problem", "Uttara", "Sector 13, Road 5", 3, PENDING, 0),

    ("Flickering streetlights on main road",
     "Several streetlights flicker and switch off at random, making the road unsafe after dark.",
     "Streetlight Problem", "Mohammadpur", "Town Hall Road", 4, RESOLVED, 15),
    ("Road damaged after utility digging",
     "The road was dug up for a utility line and left unrepaired. It is rough and dusty.",
     "Road Damage", "Mohammadpur", "Tajmahal Road", 5, VERIFIED, 2),
    ("Broken footpath tiles",
     "Some tiles on the footpath are loose.",
     "Broken Footpath", "Mohammadpur", "Mohammadpur bus stand", 0, REJECTED, 8),

    ("Exposed electrical wires",
     "Live wires are hanging low from a pole near the shops. This is dangerous, especially in the rain.",
     "Safety Concern", "Gulshan", "Gulshan 1 circle", 1, IN_PROGRESS, 4),
    ("Potholes on Gulshan Avenue",
     "A series of potholes along the avenue is slowing traffic and damaging vehicles.",
     "Road Damage", "Gulshan", "Gulshan Avenue, near DCC market", 2, PROBLEM_FIXED, 10),
    ("Blocked drain near the lake",
     "The roadside drain is blocked with plastic and silt, and dirty water is flowing onto the road.",
     "Drainage and Waterlogging", "Gulshan", "Road 103, near the lake", 3, PENDING, 1),
]

VERIFY_REMARKS = {
    VERIFIED: "Site checked by our team. Issue confirmed and added to the work queue.",
    REJECTED: "Unable to confirm the issue from the photo provided. Please resubmit with a clearer photo.",
}
STATUS_REMARKS = {
    IN_PROGRESS: "Work order created and a crew has been assigned.",
    PROBLEM_FIXED: "Repair work completed. Final inspection pending.",
    RESOLVED: "Inspected and confirmed fixed. Issue resolved.",
    CLOSED: "Hazard secured and the case has been closed.",
}

AUTHORITY_COMMENTS = [
    "Thank you for reporting. Our team has been notified.",
    "A crew will visit the site within 48 hours.",
    "Work has started on this issue.",
]
CITIZEN_COMMENTS = [
    "I walk past here every day. This really needs fixing!",
    "Same problem here, it has been like this for weeks.",
    "Thanks for reporting this, hopefully it gets fixed soon.",
    "Great to see the authorities responding quickly.",
    "This is dangerous, especially at night.",
]

# Workflow steps (after 'reported') for each final state
PHYSICAL_STEPS = {
    PENDING: [], REJECTED: [], VERIFIED: [],
    IN_PROGRESS: [Report.IN_PROGRESS],
    PROBLEM_FIXED: [Report.IN_PROGRESS, Report.PROBLEM_FIXED],
    RESOLVED: [Report.IN_PROGRESS, Report.PROBLEM_FIXED, Report.RESOLVED],
}
SAFETY_STEPS = {
    PENDING: [], REJECTED: [], VERIFIED: [],
    IN_PROGRESS: [Report.IN_PROGRESS],
    CLOSED: [Report.IN_PROGRESS, Report.CLOSED],
}


# ----------------------------------------------------------------------------
# Placeholder photo generator
# ----------------------------------------------------------------------------
def make_photo(title, subtitle, top, bottom, size=(960, 640)):
    """Return JPEG bytes: a simple gradient card with text (before/after photo)."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = size
    img = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(img)
    for y in range(h):  # vertical gradient
        t = y / h
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=color)

    def font(px):
        try:
            return ImageFont.load_default(size=px)
        except TypeError:  # very old Pillow
            return ImageFont.load_default()

    def centered(text, y, f, fill):
        box = draw.textbbox((0, 0), text, font=f)
        draw.text(((w - (box[2] - box[0])) / 2, y), text, font=f, fill=fill)

    centered(title, h * 0.36, font(72), (255, 255, 255))
    centered(subtitle, h * 0.56, font(34), (240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()



def load_photo(kind, number):
    """Return (filename, bytes) for demo_photos/<kind>_<NN>.<ext>, or None."""
    folder = Path(settings.BASE_DIR) / "demo_photos"
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = folder / f"{kind}_{number:02d}{ext}"
        if path.exists():
            return path.name, path.read_bytes()
    return None


# ----------------------------------------------------------------------------
# Command
# ----------------------------------------------------------------------------
class Command(BaseCommand):
    help = "Create demo citizens, authorities, reports, comments and votes for presentations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete existing demo users/reports first, then recreate them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(42)  # same data every run
        now = timezone.now()

        demo_usernames = (
            [c[0] for c in CITIZENS]
            + [a[0] for a in AUTHORITIES]
            + [PENDING_AUTHORITY[0]]
        )

        if options["reset"]:
            deleted, _ = User.objects.filter(username__in=demo_usernames).delete()
            self.stdout.write(f"Removed previous demo data ({deleted} rows).")
        elif User.objects.filter(username__in=demo_usernames).exists():
            self.stdout.write(self.style.WARNING(
                "Demo data already exists. Run with --reset to recreate it."))
            return

        # 1) Admin account (reuses the existing seed_admin command)
        call_command("seed_admin")
        admin_user = User.objects.filter(role=User.Role.ADMIN).order_by("id").first()

        # 2) Areas
        areas = {}
        for name, (lat, lng) in AREAS.items():
            area, _ = Area.objects.get_or_create(
                name=name,
                defaults={
                    "description": f"{name}, Dhaka",
                    "center_lat": lat,
                    "center_lng": lng,
                },
            )
            areas[name] = area

        # 3) Categories (normally created by the post_migrate signal)
        categories = {}
        from core.signals import DEFAULT_CATEGORIES
        for name, ctype in DEFAULT_CATEGORIES:
            categories[name], _ = Category.objects.get_or_create(
                name=name, type=ctype, defaults={"requires_after_photo": True})

        # 4) Citizens
        citizens = []
        for username, first, last in CITIZENS:
            citizens.append(User.objects.create_user(
                username=username, email=f"{username}@example.com",
                password=DEMO_PASSWORD, first_name=first, last_name=last,
                role=User.Role.CITIZEN,
            ))

        # 5) Authorities (approved) + one pending
        authority_by_area = {}
        for username, first, last, dept, area_name in AUTHORITIES:
            user = User.objects.create_user(
                username=username, email=f"{username}@example.com",
                password=DEMO_PASSWORD, first_name=first, last_name=last,
                role=User.Role.AUTHORITY,
            )
            profile = AuthorityProfile.objects.create(
                user=user, department=dept, assigned_area_name=area_name,
                approval_status=AuthorityProfile.ApprovalStatus.APPROVED,
                approved_by=admin_user, approved_at=now - timedelta(days=40),
            )
            authority_by_area[area_name] = profile

        username, first, last, dept, area_name = PENDING_AUTHORITY
        pending_user = User.objects.create_user(
            username=username, email=f"{username}@example.com",
            password=DEMO_PASSWORD, first_name=first, last_name=last,
            role=User.Role.AUTHORITY,
        )
        AuthorityProfile.objects.create(
            user=pending_user, department=dept, assigned_area_name=area_name,
            approval_status=AuthorityProfile.ApprovalStatus.PENDING,
        )

        # 6) Reports + verification + history
        created_reports = []
        custom_photos = 0
        for number, (title, desc, cat_name, area_name, loc, reporter_idx, state, days_ago) in enumerate(REPORTS, start=1):
            category = categories[cat_name]
            area = areas[area_name]
            authority = authority_by_area[area_name]
            reporter = citizens[reporter_idx]
            lat, lng = AREAS[area_name]
            created = now - timedelta(days=days_ago, hours=rng.randint(0, 6))

            report = Report(
                title=title, description=desc, reporter=reporter,
                category=category, area=area, location_text=loc,
                latitude=round(lat + rng.uniform(-0.008, 0.008), 6),
                longitude=round(lng + rng.uniform(-0.008, 0.008), 6),
                verification_status=(
                    VERIFIED if state not in (PENDING, REJECTED) else state),
                operational_status=Report.REPORTED,
            )
            found = load_photo("before", number)
            if found:
                custom_photos += 1
                before_name, before_bytes = found
            else:
                before_name = "before.jpg"
                before_bytes = make_photo("BEFORE", f"{cat_name} - {area_name}",
                                          (150, 70, 60), (60, 40, 40))
            report.before_image.save(before_name, ContentFile(before_bytes), save=False)
            report.save()

            steps = (SAFETY_STEPS if category.type == "safety" else PHYSICAL_STEPS)[state]

            # Verification record (for everything except pending)
            verified_at = created + timedelta(hours=rng.randint(4, 20))
            if state != PENDING:
                decision = REJECTED if state == REJECTED else VERIFIED
                v = Verification.objects.create(
                    report=report, reviewed_by=authority,
                    status=decision, remarks=VERIFY_REMARKS[decision])
                Verification.objects.filter(pk=v.pk).update(verified_at=verified_at)

            # Status history, spaced out between creation and now
            interval = max(1, days_ago // (len(steps) + 1)) if steps else 1
            previous = Report.REPORTED
            last_time = None
            for i, new_status in enumerate(steps):
                when = min(created + timedelta(days=interval * (i + 1)), now)
                note = STATUS_REMARKS[new_status]
                h = ReportStatusHistory.objects.create(
                    report=report, previous_status=previous,
                    new_status=new_status, changed_by=authority, remarks=note)
                ReportStatusHistory.objects.filter(pk=h.pk).update(changed_at=when)
                previous, last_time = new_status, when

            # Final report fields
            fields = {"created_at": created, "updated_at": last_time or verified_at}
            if steps:
                fields["operational_status"] = steps[-1]
                if steps[-1] in (Report.RESOLVED, Report.CLOSED):
                    fields["resolved_at"] = last_time
                    fields["resolution_note"] = STATUS_REMARKS[steps[-1]]
            Report.objects.filter(pk=report.pk).update(**fields)

            # After photo for repaired physical issues
            if steps and steps[-1] in (Report.PROBLEM_FIXED, Report.RESOLVED):
                report.refresh_from_db()
                found = load_photo("after", number)
                if found:
                    custom_photos += 1
                    after_name, after_bytes = found
                else:
                    after_name = "after.jpg"
                    after_bytes = make_photo("AFTER", f"{cat_name} - fixed",
                                             (60, 140, 90), (30, 80, 60))
                report.after_image.save(after_name, ContentFile(after_bytes), save=False)
                report.save(update_fields=["after_image"])
                Report.objects.filter(pk=report.pk).update(
                    updated_at=fields["updated_at"])

            created_reports.append((report, state, created, days_ago, authority))

        # 7) Comments & votes (only on reports that are publicly visible)
        for report, state, created, days_ago, authority in created_reports:
            if state in (PENDING, REJECTED):
                continue

            others = [c for c in citizens if c.pk != report.reporter_id]
            rng.shuffle(others)

            # votes
            for voter in others[: rng.randint(2, 5)]:
                Vote.objects.create(
                    user=voter, report=report,
                    vote_value=1 if rng.random() < 0.85 else -1)

            # comments: one from the authority, 1-2 from citizens
            comment_list = [(authority.user, rng.choice(AUTHORITY_COMMENTS))]
            for commenter in others[: rng.randint(1, 2)]:
                comment_list.append((commenter, rng.choice(CITIZEN_COMMENTS)))
            for i, (user, text) in enumerate(comment_list):
                c = Comment.objects.create(report=report, user=user, text=text)
                Comment.objects.filter(pk=c.pk).update(
                    created_at=min(created + timedelta(days=1 + i), now))

            # priority score (the model never sets this automatically)
            summary = report.votes.summary()
            score = summary["score"] + (5 if report.category.type == "safety" else 0)
            Report.objects.filter(pk=report.pk).update(priority_score=float(score))

        # 8) Trust-score counters for citizens
        for citizen in citizens:
            mine = Report.objects.filter(reporter=citizen)
            User.objects.filter(pk=citizen.pk).update(
                total_reports_count=mine.count(),
                verified_reports_count=mine.filter(verification_status=VERIFIED).count(),
            )
            citizen.refresh_from_db()
            citizen.update_trust_score()

        self.print_summary(custom_photos)

    def print_summary(self, custom_photos=0):
        out = self.stdout.write
        ok = self.style.SUCCESS
        out(ok("\nDemo data created successfully.\n"))
        out(f"  Reports: {Report.objects.count()}   Comments: {Comment.objects.count()}   "
            f"Votes: {Vote.objects.count()}   Your own photos used: {custom_photos}\n")
        out("Login accounts (password for all demo users: %s)" % DEMO_PASSWORD)
        out("  Admin      : admin / FixIt-Admin-2026   (from seed_admin)")
        out("  Citizens   : " + ", ".join(c[0] for c in CITIZENS))
        out("  Authorities: " + ", ".join(a[0] for a in AUTHORITIES))
        out(f"  Pending authority (for the approval demo): {PENDING_AUTHORITY[0]}\n")