//
//  generate_jd_pdf.m
//  Trainer Progression App - Professional Job Description PDF Generator
//

#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#import <PDFKit/PDFKit.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSString *html = @""
        "<!DOCTYPE html>"
        "<html><head><meta charset='utf-8'>"
        "<style>"
        "  body {"
        "    font-family: -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif;"
        "    font-size: 11pt;"
        "    line-height: 1.5;"
        "    color: #1e293b;"
        "    margin: 0;"
        "    padding: 0;"
        "  }"
        "  .header-badge {"
        "    display: inline-block;"
        "    background-color: #0284c7;"
        "    color: #ffffff;"
        "    font-size: 8pt;"
        "    font-weight: 700;"
        "    text-transform: uppercase;"
        "    letter-spacing: 0.05em;"
        "    padding: 3px 8px;"
        "    border-radius: 4px;"
        "    margin-bottom: 8px;"
        "  }"
        "  h1 {"
        "    font-size: 20pt;"
        "    font-weight: 800;"
        "    color: #0f172a;"
        "    margin: 0 0 4px 0;"
        "    letter-spacing: -0.02em;"
        "  }"
        "  .subtitle {"
        "    font-size: 11pt;"
        "    font-weight: 500;"
        "    color: #475569;"
        "    margin-bottom: 16px;"
        "  }"
        "  .meta-box {"
        "    background-color: #f8fafc;"
        "    border: 1px solid #e2e8f0;"
        "    border-left: 4px solid #0284c7;"
        "    padding: 10px 14px;"
        "    border-radius: 4px;"
        "    font-size: 9.5pt;"
        "    color: #334155;"
        "    margin-bottom: 20px;"
        "  }"
        "  .meta-row { margin-bottom: 3px; }"
        "  .meta-label { font-weight: 700; color: #0f172a; }"
        "  h2 {"
        "    font-size: 13pt;"
        "    font-weight: 700;"
        "    color: #0f172a;"
        "    border-bottom: 1.5px solid #cbd5e1;"
        "    padding-bottom: 4px;"
        "    margin-top: 18px;"
        "    margin-bottom: 10px;"
        "  }"
        "  h3 {"
        "    font-size: 11pt;"
        "    font-weight: 700;"
        "    color: #0369a1;"
        "    margin-top: 12px;"
        "    margin-bottom: 4px;"
        "  }"
        "  p, ul { margin: 0 0 10px 0; }"
        "  ul { padding-left: 18px; }"
        "  li { margin-bottom: 4px; }"
        "  .badge-focus {"
        "    background-color: #e0f2fe;"
        "    color: #0369a1;"
        "    font-size: 8pt;"
        "    font-weight: 700;"
        "    padding: 2px 6px;"
        "    border-radius: 4px;"
        "    border: 1px solid #bae6fd;"
        "  }"
        "  table {"
        "    width: 100%;"
        "    border-collapse: collapse;"
        "    margin-top: 10px;"
        "    margin-bottom: 14px;"
        "    font-size: 9pt;"
        "  }"
        "  th, td {"
        "    border: 1px solid #cbd5e1;"
        "    padding: 7px 10px;"
        "    text-align: left;"
        "    vertical-align: top;"
        "  }"
        "  th {"
        "    background-color: #f1f5f9;"
        "    color: #0f172a;"
        "    font-weight: 700;"
        "  }"
        "  tr:nth-child(even) td {"
        "    background-color: #f8fafc;"
        "  }"
        "  .highlight-card {"
        "    background-color: #f0fdf4;"
        "    border: 1px solid #bbf7d0;"
        "    border-left: 4px solid #16a34a;"
        "    padding: 10px 14px;"
        "    border-radius: 4px;"
        "    margin-top: 14px;"
        "    margin-bottom: 14px;"
        "  }"
        "</style></head><body>"
        "<div class='header-badge'>Target Role &amp; Occupational Specification</div>"
        "<h1>Job Description: Independent Personal Trainer</h1>"
        "<div class='subtitle'>Resistance Training Specialist &bull; Strength &amp; Conditioning Coach</div>"
        ""
        "<div class='meta-box'>"
        "  <div class='meta-row'><span class='meta-label'>Standard Occupational Classification:</span> O*NET 39-9031.00 / U.S. Bureau of Labor Statistics (BLS)</div>"
        "  <div class='meta-row'><span class='meta-label'>Industry Domain:</span> Health, Fitness Coaching &amp; Athletic Performance</div>"
        "  <div class='meta-row'><span class='meta-label'>Delivery Model:</span> Independent Coach &bull; Private Studio &bull; Hybrid Remote Programming (10–35+ Clients)</div>"
        "  <div class='meta-row'><span class='meta-label'>Product Alignment:</span> Target User Profile &amp; Workflow Specifications for <strong>Trainer Progression App</strong></div>"
        "</div>"
        ""
        "<h2>1. Occupational Summary &amp; Purpose</h2>"
        "<p>The <strong>Personal Trainer / Strength &amp; Conditioning Coach</strong> is an exercise professional responsible for evaluating physical capabilities, designing tailored multi-week resistance training programs, instructing biomechanically safe movement patterns, and tracking athletic progression over time. Operating primarily as independent contractors, studio coaches, or hybrid trainers, they manage athlete progression while actively preventing acute and chronic training injuries.</p>"
        ""
        "<h2>2. The 4 Core Occupational Duties (O*NET 39-9031.00)</h2>"
        "<p>The U.S. Bureau of Labor Statistics and O*NET delineate four core functional duties for fitness trainers. Two of these duties occur continuously every single week for every client on the roster, forming the primary design target of the Trainer Progression App:</p>"
        ""
        "<h3>Duty 1: Assess Abilities, Health History &amp; Goals</h3>"
        "<ul>"
        "  <li>Conduct initial health history interviews, lifestyle audits, and physical readiness evaluations.</li>"
        "  <li>Document and maintain longitudinal records of past musculoskeletal injuries, surgeries, and chronic impingements (e.g., shoulder, lumbar, knee issues).</li>"
        "  <li>Define measurable strength, hypertrophy, and functional milestones across training blocks.</li>"
        "</ul>"
        ""
        "<h3>Duty 2: Create &amp; Adjust Progressive Training Programs <span class='badge-focus'>Primary App Focus</span></h3>"
        "<ul>"
        "  <li>Construct tailored multi-week training programs balancing volume, intensity, exercise selection, and recovery.</li>"
        "  <li>Apply systematic, deterministic overload rules (e.g., reps-first progression advancing repetitions to target ceilings before escalating load).</li>"
        "  <li>Recalculate weekly weights, sets, and reps based on logged performance and client effort ratings (RPE).</li>"
        "  <li>Dynamically hold or deload lifts when joint discomfort, fatigue, or form degradation is identified.</li>"
        "</ul>"
        ""
        "<h3>Duty 3: Monitor Client Progress &amp; Adherence <span class='badge-focus'>Primary App Focus</span></h3>"
        "<ul>"
        "  <li>Track workout completion logs, actual reps achieved, weights moved, and perceived exertion ratings.</li>"
        "  <li>Actively cross-reference in-session feedback against historical injury profiles to intercept emerging pain flags.</li>"
        "  <li>Triage client rosters weekly to identify clients with declining workout frequency, missed check-ins, or silence.</li>"
        "  <li>Deliver proactive, encouraging outreach and check-ins to maintain client accountability and long-term retention.</li>"
        "</ul>"
        ""
        "<h3>Duty 4: Teach Lifting Technique, Biomechanics &amp; Safety</h3>"
        "<ul>"
        "  <li>Demonstrate and instruct proper lifting form, bar path, setup, bracing, and joint positioning.</li>"
        "  <li>Observe live execution, delivering immediate verbal and physical cues to correct technical breakdown.</li>"
        "  <li>Ensure safe gym floor practices, equipment maintenance, and injury risk mitigation.</li>"
        "</ul>"
        ""
        "<h2>3. Critical Pain Points in Traditional Trainer Workflows</h2>"
        "<ul>"
        "  <li><strong>Severe Administrative Overhead:</strong> Independent trainers lose <strong>3 to 8 hours every weekend</strong> performing administrative chores: manually reviewing fragmented text messages, transcribing messy notes, and editing Google Sheets lift by lift.</li>"
        "  <li><strong>Repetitive Mathematical Math:</strong> Recalculating deterministic rep/weight progression formulas across 20+ clients and 100+ exercises each week causes severe decision fatigue.</li>"
        "  <li><strong>In-Gym Logging Friction:</strong> Clients training independently dislike navigating multi-click mobile forms or native app logins with sweaty hands, often resorting to cryptic texts (<em>\"did bench 135x10, squats felt ok\"</em>) or logging nothing at all.</li>"
        "  <li><strong>Signal Loss &amp; Injury Risk:</strong> Subtle pain notes sent via SMS (<em>\"shoulder was pinching on set 3\"</em>) get buried in chat histories, leading to unaddressed joint strain.</li>"
        "  <li><strong>Client Churn from Inactivity:</strong> Disengaged clients quietly stop training without the coach noticing until subscription renewals lapse.</li>"
        "</ul>"
        ""
        "<h2>4. How the Trainer Progression App Solves These Responsibilities</h2>"
        "<table>"
        "  <tr>"
        "    <th style='width: 25%;'>Trainer Duty</th>"
        "    <th style='width: 33%;'>Traditional Inefficiency</th>"
        "    <th style='width: 42%;'>Trainer Progression App Architecture</th>"
        "  </tr>"
        "  <tr>"
        "    <td><strong>Client Logging &amp; Intake</strong></td>"
        "    <td>Clunky apps, forgotten passwords, dropped client compliance.</td>"
        "    <td><strong>Workout Logger (Claude Sonnet 5.5):</strong> Passwordless magic link (<code>/s/:token</code>), natural voice/chat transcription, and 1-tap confirmation.</td>"
        "  </tr>"
        "  <tr>"
        "    <td><strong>Weekly Program Progression</strong></td>"
        "    <td>Hours of manual spreadsheet formula recalculations.</td>"
        "    <td><strong>Deterministic Progression Engine:</strong> Pure Python algorithms compute mathematical progressions with zero hallucination.</td>"
        "  </tr>"
        "  <tr>"
        "    <td><strong>Injury &amp; Safety Monitoring</strong></td>"
        "    <td>Buried text messages and missed pain warnings.</td>"
        "    <td><strong>Progression Planner (Claude Haiku 5.5):</strong> Flags held lifts conflicting with historical injuries on the coach's triage queue.</td>"
        "  </tr>"
        "  <tr>"
        "    <td><strong>Programming Authority</strong></td>"
        "    <td>Loss of control from black-box AI apps.</td>"
        "    <td><strong>Human-in-the-Loop Gate:</strong> Auto-drafted plans remain in draft state until reviewed and approved via 1-click trainer signoff.</td>"
        "  </tr>"
        "  <tr>"
        "    <td><strong>Client Adherence &amp; Retention</strong></td>"
        "    <td>Silent disengagement and lost subscription revenue.</td>"
        "    <td><strong>Trainer Assistant (Claude Sonnet 5.5):</strong> Automated triage feed surfaces inactive athletes and drafts personalized outreach.</td>"
        "  </tr>"
        "</table>"
        ""
        "<div class='highlight-card'>"
        "  <strong>Quantified Professional Impact:</strong>"
        "  <ul>"
        "    <li><strong>75% Time Reduction:</strong> Cuts weekly programming administration from ~6.7 hours down to ~1.7 hours.</li>"
        "    <li><strong>Capacity Expansion:</strong> Allows independent trainers to scale active rosters from 20 up to <strong>35+ clients</strong> without quality degradation.</li>"
        "    <li><strong>Enhanced Client Longevity:</strong> Proactive pain interception and automated adherence triage substantially curb client dropout rates.</li>"
        "  </ul>"
        "</div>"
        ""
        "</body></html>";

        NSData *data = [html dataUsingEncoding:NSUTF8StringEncoding];
        NSDictionary *options = @{
            NSDocumentTypeDocumentAttribute: NSHTMLTextDocumentType,
            NSCharacterEncodingDocumentAttribute: @(NSUTF8StringEncoding)
        };
        
        NSAttributedString *attrString = [[NSAttributedString alloc] initWithData:data options:options documentAttributes:nil error:nil];
        if (!attrString) {
            NSLog(@"Error: Failed to parse HTML into attributed string");
            return 1;
        }

        // US Letter size in points: 612 x 792 pt (8.5 x 11 inches)
        CGFloat pageWidth = 612.0;
        CGFloat pageHeight = 792.0;
        CGFloat marginX = 46.0;
        CGFloat marginTop = 46.0;
        CGFloat marginBottom = 46.0;
        CGFloat contentWidth = pageWidth - (2 * marginX);
        CGFloat contentHeight = pageHeight - marginTop - marginBottom;

        NSTextStorage *textStorage = [[NSTextStorage alloc] initWithAttributedString:attrString];
        NSLayoutManager *layoutManager = [[NSLayoutManager alloc] init];
        [textStorage addLayoutManager:layoutManager];

        NSMutableArray<NSTextContainer *> *containers = [NSMutableArray array];
        NSUInteger glyphIndex = 0;

        while (glyphIndex < [layoutManager numberOfGlyphs]) {
            NSTextContainer *container = [[NSTextContainer alloc] initWithContainerSize:NSMakeSize(contentWidth, contentHeight)];
            [container setLineFragmentPadding:0];
            [layoutManager addTextContainer:container];
            [containers addObject:container];

            NSRange range = [layoutManager glyphRangeForTextContainer:container];
            glyphIndex = NSMaxRange(range);
        }

        NSUInteger pageCount = [containers count];
        NSLog(@"Layout generated %lu pages for Job Description PDF", (unsigned long)pageCount);

        NSString *outputPath = @"documents/personal-trainer-job-description.pdf";
        NSURL *outputURL = [NSURL fileURLWithPath:outputPath];

        NSMutableData *pdfData = [NSMutableData data];
        CGDataConsumerRef consumer = CGDataConsumerCreateWithCFData((__bridge CFMutableDataRef)pdfData);
        CGRect mediaBox = CGRectMake(0, 0, pageWidth, pageHeight);
        CGContextRef pdfContext = CGPDFContextCreate(consumer, &mediaBox, NULL);

        for (NSUInteger i = 0; i < pageCount; i++) {
            CGPDFContextBeginPage(pdfContext, NULL);
            NSGraphicsContext *nsContext = [NSGraphicsContext graphicsContextWithCGContext:pdfContext flipped:NO];
            [NSGraphicsContext saveGraphicsState];
            [NSGraphicsContext setCurrentContext:nsContext];

            // Header line on subsequent pages
            if (i > 0) {
                NSDictionary *hdrAttrs = @{
                    NSFontAttributeName: [NSFont systemFontOfSize:8 weight:NSFontWeightMedium],
                    NSForegroundColorAttributeName: [NSColor colorWithCalibratedRed:0.4 green:0.45 blue:0.55 alpha:1.0]
                };
                NSString *hdrText = @"TRAINER PROGRESSION APP — JOB DESCRIPTION: INDEPENDENT PERSONAL TRAINER (O*NET 39-9031.00)";
                [hdrText drawAtPoint:NSMakePoint(marginX, pageHeight - marginTop + 14) withAttributes:hdrAttrs];
                
                // Hairline
                CGContextSetStrokeColorWithColor(pdfContext, [[NSColor colorWithCalibratedWhite:0.85 alpha:1.0] CGColor]);
                CGContextSetLineWidth(pdfContext, 0.5);
                CGContextMoveToPoint(pdfContext, marginX, pageHeight - marginTop + 8);
                CGContextAddLineToPoint(pdfContext, pageWidth - marginX, pageHeight - marginTop + 8);
                CGContextStrokePath(pdfContext);
            }

            // Draw text content
            NSRange glyphRange = [layoutManager glyphRangeForTextContainer:containers[i]];
            NSPoint drawPoint = NSMakePoint(marginX, pageHeight - marginTop - contentHeight);
            
            // CoreGraphics coordinate transformation
            CGContextSaveGState(pdfContext);
            CGContextTranslateCTM(pdfContext, marginX, pageHeight - marginTop);
            CGContextScaleCTM(pdfContext, 1.0, -1.0);
            
            [layoutManager drawGlyphsForGlyphRange:glyphRange atPoint:NSZeroPoint];
            CGContextRestoreGState(pdfContext);

            // Footer line & page numbers
            CGContextSetStrokeColorWithColor(pdfContext, [[NSColor colorWithCalibratedWhite:0.85 alpha:1.0] CGColor]);
            CGContextSetLineWidth(pdfContext, 0.5);
            CGContextMoveToPoint(pdfContext, marginX, marginBottom - 10);
            CGContextAddLineToPoint(pdfContext, pageWidth - marginX, marginBottom - 10);
            CGContextStrokePath(pdfContext);

            NSDictionary *ftrAttrs = @{
                NSFontAttributeName: [NSFont systemFontOfSize:8.5 weight:NSFontWeightRegular],
                NSForegroundColorAttributeName: [NSColor colorWithCalibratedRed:0.45 green:0.5 blue:0.6 alpha:1.0]
            };
            NSString *ftrLeft = @"O*NET 39-9031.00 &bull; U.S. Bureau of Labor Statistics &bull; Trainer Progression App System Specification";
            [ftrLeft drawAtPoint:NSMakePoint(marginX, marginBottom - 24) withAttributes:ftrAttrs];

            NSString *ftrRight = [NSString stringWithFormat:@"Page %lu of %lu", (unsigned long)(i + 1), (unsigned long)pageCount];
            NSSize rightSize = [ftrRight sizeWithAttributes:ftrAttrs];
            [ftrRight drawAtPoint:NSMakePoint(pageWidth - marginX - rightSize.width, marginBottom - 24) withAttributes:ftrAttrs];

            [NSGraphicsContext restoreGraphicsState];
            CGPDFContextEndPage(pdfContext);
        }

        CGPDFContextClose(pdfContext);
        CGContextRelease(pdfContext);
        CGDataConsumerRelease(consumer);

        BOOL success = [pdfData writeToURL:outputURL atomically:YES];
        if (success) {
            NSLog(@"SUCCESS: Rendered %lu-page Job Description PDF at %@", (unsigned long)pageCount, outputPath);
        } else {
            NSLog(@"ERROR: Failed to write PDF to %@", outputPath);
            return 1;
        }
    }
    return 0;
}
