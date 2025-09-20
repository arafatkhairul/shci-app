import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const { text, language = 'en' } = await request.json();
        
        // Call the backend TTS service
        const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
        const ttsResponse = await fetch(`${backendUrl}/tts/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                language: language
            })
        });

        if (!ttsResponse.ok) {
            throw new Error(`Backend TTS failed: ${ttsResponse.status}`);
        }

        const ttsData = await ttsResponse.json();
        
        if (ttsData.status === 'success' && ttsData.audio_base64) {
            // Convert base64 audio to buffer
            const audioBuffer = Buffer.from(ttsData.audio_base64, 'base64');
            
            return new NextResponse(audioBuffer, {
                headers: {
                    'Content-Type': 'audio/wav',
                    'Content-Length': audioBuffer.length.toString()
                }
            });
        } else {
            throw new Error('TTS synthesis failed');
        }
    } catch (error) {
        console.error('TTS API error:', error);
        return NextResponse.json({ error: 'TTS test failed' }, { status: 500 });
    }
}

