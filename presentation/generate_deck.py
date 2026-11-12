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
import shutil
import subprocess
import tempfile
import zipfile
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
            "This slide is the Loom walkthrough. It starts when the slideshow reaches this slide. "
            "If you are still looking at the still picture, click it once.\n\n"
            "PowerPoint cannot show the Loom web player, so this file contains the same recording."
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


def prepare_powerpoint_video(source_path):
    """
    Makes a copy of the walkthrough that PowerPoint and Keynote will play.

    The original file is H.264 High. Some presentation apps open that file
    and only show the still picture. This copy uses the older Baseline
    picture style, keeps the sound, and puts the index at the front of the
    file so playback can start immediately. The browser deck keeps using
    the original file.
    """
    # Keep the real filename. PowerPoint uses it as the movie's name,
    # and a random temp name can make the file look like a broken link.
    dest_dir = tempfile.mkdtemp()
    dest_path = os.path.join(dest_dir, "loom-walkthrough.mp4")
    command = [
        "ffmpeg", "-y", "-i", source_path,
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.1",
        "-pix_fmt", "yuv420p", "-bf", "0", "-crf", "20", "-preset", "medium",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        dest_path,
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return dest_path


def make_embedded_video_playable(pptx_path):
    """
    Fixes the movie slide after python-pptx writes it.

    The builder leaves the play action pointing at a blank link, so a click
    does nothing and the still picture stays up. This removes that blank
    link and tells the slideshow to start the video when the slide appears.
    """
    with zipfile.ZipFile(pptx_path, "r") as source:
        slide_name = "ppt/slides/slide9.xml"
        slide_xml = source.read(slide_name).decode("utf-8")
        other_parts = [
            item for item in source.infolist()
            if item.filename != slide_name
        ]
        payloads = {item.filename: source.read(item.filename) for item in other_parts}

    slide_xml = slide_xml.replace(' r:id=""', "")
    # A full slideshow timeline is what PowerPoint and Keynote look for.
    # The short one python-pptx writes never starts the movie.
    play_on_open = (
        "<p:timing><p:tnLst><p:par>"
        '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
        '<p:childTnLst><p:seq concurrent="1" nextAc="seek">'
        '<p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst><p:par>'
        '<p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
        "<p:childTnLst><p:video><p:cMediaNode vol=\"80000\">"
        '<p:cTn id="4" fill="hold" display="0">'
        '<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
        '<p:tgtEl><p:spTgt spid="2"/></p:tgtEl>'
        "</p:cMediaNode></p:video></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>"
        '<p:prevCondLst><p:cond evt="onPrev" delay="0">'
        "<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>"
        '<p:nextCondLst><p:cond evt="onNext" delay="0">'
        "<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>"
        "</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>"
    )
    start = slide_xml.find("<p:timing>")
    end = slide_xml.find("</p:timing>")
    if start != -1 and end != -1:
        slide_xml = slide_xml[:start] + play_on_open + slide_xml[end + len("</p:timing>"):]
    if "xmlns:p14=" not in slide_xml.split(">", 1)[0]:
        slide_xml = slide_xml.replace(
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"',
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"',
            1,
        )

    temp_path = pptx_path + ".tmp"
    with zipfile.ZipFile(temp_path, "w") as rebuilt:
        for item in other_parts:
            # Copy each existing part as-is, including the video, so the
            # repair only changes the slide that holds the play button.
            copied = zipfile.ZipInfo(filename=item.filename, date_time=item.date_time)
            copied.compress_type = item.compress_type
            copied.external_attr = item.external_attr
            rebuilt.writestr(copied, payloads[item.filename])
        slide_info = zipfile.ZipInfo(filename=slide_name)
        slide_info.compress_type = zipfile.ZIP_DEFLATED
        rebuilt.writestr(slide_info, slide_xml.encode("utf-8"))
    shutil.move(temp_path, pptx_path)


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

        # Slide 9 is the walkthrough. The movie fills the slide. The still
        # picture is what shows until the slideshow starts the video.
        video_path = os.path.join(base_dir, "loom-walkthrough.mp4")
        poster_path = os.path.join(slides_dir, "loom-poster.jpg")
        compatible_video = None
        if num == 9 and os.path.exists(video_path):
            try:
                compatible_video = prepare_powerpoint_video(video_path)
                movie_path = compatible_video
            except (subprocess.CalledProcessError, FileNotFoundError):
                movie_path = video_path
            slide.shapes.add_movie(
                movie_path,
                left=Inches(0),
                top=Inches(0),
                width=prs.slide_width,
                height=prs.slide_height,
                poster_frame_image=poster_path if os.path.exists(poster_path) else img_path,
                mime_type="video/mp4",
            )
            if compatible_video and os.path.exists(compatible_video):
                shutil.rmtree(os.path.dirname(compatible_video), ignore_errors=True)
        else:
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
    # python-pptx saves a movie that looks right but will not start. This
    # pass repairs the play action so the slideshow actually runs the video.
    make_embedded_video_playable(out_pptx)
    print(f"\nSuccessfully saved PowerPoint presentation to: {out_pptx}")


if __name__ == "__main__":
    create_powerpoint_presentation()
