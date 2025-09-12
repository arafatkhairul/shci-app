import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const { text, language } = await request.json();
        
        // Simple test response - in production this would call the backend TTS
        const testAudio = Buffer.from('test audio data').toString('base64');
        
        return new NextResponse(Buffer.from(testAudio, 'base64'), {
            headers: {
                'Content-Type': 'audio/mp3',
                'Content-Length': testAudio.length.toString()
            }
        });
    } catch (error) {
        return NextResponse.json({ error: 'TTS test failed' }, { status: 500 });
    }
}

