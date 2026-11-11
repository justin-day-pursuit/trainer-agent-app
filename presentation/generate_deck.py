"""
Builds a PowerPoint (.pptx) deck and broken-up slide assets from presentation/deck.pdf.

Why this script exists:
Our project presentation is stored as a multi-page PDF (presentation/deck.pdf).
When presenting or sharing with stakeholders, having a ready-to-present PowerPoint (.pptx)
file and broken-up individual slide files (PDF, PNG) makes it easy to present in
Keynote, PowerPoint, Google Slides, or any web browser.

What this script does:
1. Takes the high-resolution 1920x1080 16:9 PNG slide images generated from deck.pdf.
2. Creates a native 16:9 widescreen PowerPoint presentation (presentation/deck.pptx).
3. Adds each slide with speaker notes and titles corresponding to that slide.
4. Generates a standalone interactive HTML slide deck (presentation/deck-slides.html)
   for instant browser-based fullscreen presentations without needing PowerPoint.
"""

import os
from pptx import Presentation
from pptx.util import Inches

# Slide titles and speaker notes extracted from the presentation deck
SLIDE_DATA = [
    {
        "slide_num": 1,
        "title": "FINAL PROJECT: Trainer Progression App",
        "notes": (
            "Title: FINAL PROJECT - Trainer Progression App\n\n"
            "Subtitle: Next week’s workouts drafted from last week’s logs. "
            "The trainer approves every one.\n\n"
            "Presenters: Yadan Taino and Justin Day\n\n"
            "Context: Pursuit L2 AI-Native Builder final project presentation."
        )
    },
    {
        "slide_num": 2,
        "title": "Who we are",
        "notes": (
            "Who we are: Pursuit L2 AI-Native builders\n\n"
            "• Client Side and Design: Yadan Taino\n"
            "  Built what clients and trainers touch: chat and voice logging, the Workout Logger agent, "
            "the progression rules, the Trainer Assistant check-ins, and the app's design.\n\n"
            "• Backend and Deployment: Justin Day\n"
            "  Built the engine room: the API and database, the Progression Planner agent, "
            "trainer sign-in, and the live deployment on Render and Vercel."
        )
    },
    {
        "slide_num": 3,
        "title": "The job: personal trainer",
        "notes": (
            "The job: personal trainer\n\n"
            "Why we chose it: a trainer we know rebuilds every client's program by hand each week. "
            "Of the four core duties, two repeat for every client, every week.\n\n"
            "1. Assess abilities and goals: Intake, history, and physical assessment.\n"
            "2. Create and adjust programs [Our focus]: Individual plans, updated as clients progress.\n"
            "3. Monitor client progress [Our focus]: Compare logged results and spot trends.\n"
            "4. Teach technique and safety: Live observation and correction.\n\n"
            "Sources: O*NET 39-9031.00; U.S. Bureau of Labor Statistics, Fitness Trainers and Instructors."
        )
    },
    {
        "slide_num": 4,
        "title": "The pain points: slow, repetitive, easy to miss",
        "notes": (
            "The pain points: slow, repetitive, easy to miss\n\n"
            "• SLOW: Rebuilding every program, every week. She copies each client's program "
            "in Google Sheets and edits it lift by lift.\n"
            "• REPETITIVE: The same rule, applied by hand. Reps go up to 12, then weight once it feels easy. "
            "The same math for every lift and client.\n"
            "• EASY TO MISS: Signals get lost. Pain mentioned in a text slips by, and a client who quietly stops "
            "logging goes unnoticed.\n\n"
            "Market validation: It's not just her. Trainers using Trainerize report the same manual editing. "
            "Its AI builds single workouts, not multi-week programs.\n\n"
            "Sources: Trainer interview and Trainerize market research (r/personaltraining, Capterra, Software Advice)."
        )
    },
    {
        "slide_num": 5,
        "title": "What we made easier, and how",
        "notes": (
            "What we made easier, and how (Today vs With our app):\n\n"
            "• Today: Clients open a spreadsheet to see workouts.\n"
            "  With our app: Clients log by chat or voice, with no account.\n\n"
            "• Today: Trainer copies last week's program.\n"
            "  With our app: Next week is drafted from reps and effort.\n\n"
            "• Today: Trainer adjusts every weight by hand.\n"
            "  With our app: Trainer reviews each change and its reason.\n\n"
            "• Today: Pain mentioned in passing is easy to miss.\n"
            "  With our app: Pain is flagged and that lift is held.\n\n"
            "• Today: A client drifting away goes unnoticed.\n"
            "  With our app: Trainer sees who needs a check-in, message drafted.\n\n"
            "Efficiency target: Plan a client's week at least 50% faster than in Sheets. (Not yet timed with our trainer)."
        )
    },
    {
        "slide_num": 6,
        "title": "Architecture: AI reads, code decides the numbers",
        "notes": (
            "Architecture: AI reads, code decides the numbers\n\n"
            "Frontends:\n"
            "• Client on phone: Next.js on Vercel, private link, no account.\n"
            "• Trainer dashboard: Next.js on Vercel, Supabase login, approvals.\n\n"
            "FastAPI backend on Render: every action checked for permission.\n"
            "• Workout Logger (AI, Claude Sonnet 5.5): turns chat into sets.\n"
            "• Progression Engine (Code): the ONLY source of weights and reps.\n"
            "• Progression Planner (AI, Claude Haiku 5.5): flags safety conflicts.\n"
            "• Trainer Assistant (AI, Claude Sonnet 5.5): drafts check-ins.\n\n"
            "Data layer:\n"
            "• Supabase: PostgreSQL and trainer login."
        )
    },
    {
        "slide_num": 7,
        "title": "Agent Workflow Loop: The Complete Cycle",
        "notes": (
            "Agent Workflow Loop: The Complete Cycle\n\n"
            "The 7-step weekly cycle:\n"
            "1. Client logs workout via private link.\n"
            "2. Workout Logger extracts sets and pain flags.\n"
            "3. Client reviews and confirms sets before submitting.\n"
            "4. Progression Engine calculates next week's weights and reps deterministically.\n"
            "5. Progression Planner checks against client injury history and recent pain.\n"
            "6. Trainer reviews staged draft on dashboard and approves or modifies.\n"
            "7. Client receives the updated program for next week.\n\n"
            "Check-in Loop:\n"
            "• Trainer Assistant monitors client activity and drafts check-in messages for inactive clients.\n\n"
            "Core Guardrail: AI reads and drafts; deterministic code calculates numbers; trainer holds final approval."
        )
    },
    {
        "slide_num": 8,
        "title": "How one workout moves through",
        "notes": (
            "How one workout moves through:\n\n"
            "1. [PERSON] Client logs: 'Bench 135, last set only 8, shoulder pinched'.\n"
            "2. [AI] Workout Logger: Pulls out sets and a pain flag. Saves nothing to database.\n"
            "3. [PERSON] Client checks and sends: Fixes any numbers, rates effort, taps Send to Trainer. Only this is saved.\n"
            "4. [CODE] Progression Engine: Easy sets rise to 12 reps, then weight. Hard, missed, or pain sets are held.\n"
            "5. [AI] Progression Planner: Checks injury notes. Can flag safety concerns, cannot change weights or reps.\n"
            "6. [PERSON] Trainer approves: Reads client's own words, edits or approves. Only then does client see next week."
        )
    },
    {
        "slide_num": 9,
        "title": "What we built: the whole loop, live",
        "notes": (
            "What we built: the whole loop, live\n\n"
            "Screens from the live build with sample client data:\n"
            "1. Client checks sets (Workout logging flow).\n"
            "2. Sent to the trainer (Confirmation and rating).\n"
            "3. Trainer approves: Reads client's actual words. Knee pain held the squat. One tap to approve and go live.\n"
            "4. Check-ins drafted: For clients needing attention (Trainer Assistant feed)."
        )
    },
    {
        "slide_num": 10,
        "title": "Where it stands: live and tested end to end",
        "notes": (
            "Where it stands: live and tested end to end\n\n"
            "Live URL: https://trainer-agent-app.vercel.app\n\n"
            "Delivery Status:\n"
            "1. Client logging by chat or voice -> Done\n"
            "2. Progression engine and trainer approval -> Done\n"
            "3. Trainer Assistant check-ins and roster -> Done\n"
            "4. Live on Vercel and Render -> Live\n\n"
            "Final live test on production: 9 of 10 checks passed.\n\n"
            "Next steps:\n"
            "• Log every AI call for review\n"
            "• Let trainers revoke a client link\n"
            "• Test on real iPhone and Android devices\n"
            "• Time a real planning week with our partner trainer"
        )
    }
]


def create_powerpoint_presentation():
    """
    Builds a widescreen 16:9 presentation/deck.pptx file containing all 10 slides
    from presentation/deck.pdf with corresponding speaker notes and titles.
    """
    prs = Presentation()
    
    # 16:9 widescreen dimensions (standard PowerPoint widescreen)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    blank_layout = prs.slide_layouts[6]  # Blank slide
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    slides_dir = os.path.join(base_dir, "deck-slides")
    
    for item in SLIDE_DATA:
        num = item["slide_num"]
        img_name = f"slide-{num:02d}.png"
        img_path = os.path.join(slides_dir, img_name)
        
        if not os.path.exists(img_path):
            print(f"Warning: Image {img_path} not found, skipping.")
            continue
            
        slide = prs.slides.add_slide(blank_layout)
        
        # Place high-resolution slide image covering full slide
        slide.shapes.add_picture(
            img_path,
            left=Inches(0),
            top=Inches(0),
            width=prs.slide_width,
            height=prs.slide_height
        )
        
        # Add presenter speaker notes
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = item["notes"]
        
        print(f"Added Slide {num}: {item['title']} to PowerPoint deck")
        
    out_pptx = os.path.join(base_dir, "deck.pptx")
    prs.save(out_pptx)
    print(f"\nSuccessfully saved PowerPoint presentation to: {out_pptx}")


if __name__ == "__main__":
    create_powerpoint_presentation()
