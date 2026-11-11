//
//  render_slides.m
//  Trainer Progression App - Presentation Slide Splitter
//
//  What this file does:
//  This script opens presentation/deck.pdf using macOS native PDFKit and AppKit,
//  splits the multi-page PDF into 10 individual single-page PDFs (slide-01.pdf .. slide-10.pdf),
//  and renders each page into a crisp 1920x1080 16:9 PNG image (slide-01.png .. slide-10.png).
//
//  Why it connects to the system:
//  It provides the source image and PDF assets needed by generate_deck.py (for PowerPoint)
//  and slides.html (for browser-based presentations).
//
//  To compile and run:
//  clang -framework Foundation -framework PDFKit -framework AppKit -o render_slides render_slides.m
//  ./render_slides
//

#import <Foundation/Foundation.h>
#import <PDFKit/PDFKit.h>
#import <AppKit/AppKit.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSString *basePath = @"presentation";
        NSString *pdfPath = [basePath stringByAppendingPathComponent:@"deck.pdf"];
        NSURL *url = [NSURL fileURLWithPath:pdfPath];
        
        PDFDocument *doc = [[PDFDocument alloc] initWithURL:url];
        if (!doc) {
            NSLog(@"Error: Failed to open %@", pdfPath);
            return 1;
        }
        
        NSString *outDir = [basePath stringByAppendingPathComponent:@"deck-slides"];
        [[NSFileManager defaultManager] createDirectoryAtPath:outDir withIntermediateDirectories:YES attributes:nil error:nil];
        
        NSInteger count = [doc pageCount];
        NSLog(@"Found %ld pages in %@. Splitting and rendering to 1920x1080...", (long)count, pdfPath);
        
        for (NSInteger i = 0; i < count; i++) {
            PDFPage *page = [doc pageAtIndex:i];
            NSRect bounds = [page boundsForBox:kPDFDisplayBoxMediaBox];
            
            // Standard 16:9 presentation dimensions
            CGFloat targetWidth = 1920.0;
            CGFloat targetHeight = 1080.0;
            
            NSBitmapImageRep *rep = [[NSBitmapImageRep alloc]
                                     initWithBitmapDataPlanes:NULL
                                     pixelsWide:(NSInteger)targetWidth
                                     pixelsHigh:(NSInteger)targetHeight
                                     bitsPerSample:8
                                     samplesPerPixel:4
                                     hasAlpha:YES
                                     isPlanar:NO
                                     colorSpaceName:NSDeviceRGBColorSpace
                                     bytesPerRow:0
                                     bitsPerPixel:0];
            
            NSGraphicsContext *context = [NSGraphicsContext graphicsContextWithBitmapImageRep:rep];
            [NSGraphicsContext saveGraphicsState];
            [NSGraphicsContext setCurrentContext:context];
            
            // White slide background
            [[NSColor whiteColor] set];
            NSRectFill(NSMakeRect(0, 0, targetWidth, targetHeight));
            
            CGContextRef cgContext = (CGContextRef)[context CGContext];
            CGContextSaveGState(cgContext);
            CGContextScaleCTM(cgContext, targetWidth / bounds.size.width, targetHeight / bounds.size.height);
            
            [page drawWithBox:kPDFDisplayBoxMediaBox toContext:cgContext];
            
            CGContextRestoreGState(cgContext);
            [NSGraphicsContext restoreGraphicsState];
            
            // Write PNG
            NSData *pngData = [rep representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
            NSString *imgPath = [NSString stringWithFormat:@"%@/slide-%02ld.png", outDir, (long)(i + 1)];
            [pngData writeToFile:imgPath atomically:YES];
            
            // Write standalone single-page PDF
            PDFDocument *singleDoc = [[PDFDocument alloc] init];
            [singleDoc insertPage:page atIndex:0];
            NSString *singlePdfPath = [NSString stringWithFormat:@"%@/slide-%02ld.pdf", outDir, (long)(i + 1)];
            [singleDoc writeToFile:singlePdfPath];
            
            NSLog(@"Extracted slide-%02ld: PNG (%ld bytes), PDF (%ld bytes)",
                  (long)(i + 1), (long)[pngData length], (long)[singleDoc dataRepresentation].length);
        }
        
        NSLog(@"Successfully broke up %ld slides in %@", (long)count, outDir);
    }
    return 0;
}
