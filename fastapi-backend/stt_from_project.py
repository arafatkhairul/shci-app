import time
import logging
from RealtimeSTT import AudioToTextRecorder

# লগিং সেটআপ করা হচ্ছে, যাতে আমরা প্রক্রিয়াটি দেখতে পারি
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    print("রিয়েল-টাইম ট্রান্সক্রিপশন শুরু হচ্ছে...")
    print("কথা বলা শুরু করুন (বন্ধ করতে Ctrl+C চাপুন)")

    # এই ভেরিয়েবলটি আগের টেক্সট মনে রাখবে, যাতে শুধু নতুন অংশ প্রিন্ট করা যায়
    previous_text = ""

    def on_realtime_transcription_update(text: str):
        """
        এই ফাংশনটি শুধু নতুন টেক্সট খণ্ডগুলো প্রিন্ট করে।
        """
        global previous_text
        
        # আগের টেক্সট থেকে নতুন অংশটুকু আলাদা করা হচ্ছে
        new_chunk = text[len(previous_text):]
        
        # নতুন অংশটুকু প্রিন্ট করা হচ্ছে কোনো নতুন লাইন ছাড়া
        print(new_chunk, end="", flush=True)
        
        # বর্তমান টেক্সটকে আগের টেক্সট হিসেবে সেভ করা হচ্ছে
        previous_text = text

    def on_sentence_finish(text: str):
        """
        একটি বাক্য শেষ হলে এই ফাংশনটি কল করা হবে।
        এটি একটি নতুন লাইন প্রিন্ট করে এবং পরবর্তী বাক্যের জন্য প্রস্তুত হয়।
        """
        global previous_text
        print() # বাক্য শেষে একটি নতুন লাইন তৈরি করে
        previous_text = "" # পরবর্তী বাক্যের জন্য রিসেট করা হচ্ছে


    # AudioToTextRecorder অবজেক্ট তৈরি করা হচ্ছে
    recorder = AudioToTextRecorder(
        model="base.en",  # ব্যবহৃত মডেল (যেমন: 'tiny.en', 'base.en', 'small.en')
        language="en",  # ভাষা ইংরেজি নির্ধারণ করা হয়েছে
        use_microphone=True,  # মাইক্রোফোন থেকে ইনপুট নেওয়া হবে
        on_realtime_transcription_update=on_realtime_transcription_update,
        on_realtime_transcription_stabilized=on_sentence_finish, # একটি বাক্য শেষ হলে কল করা হবে
        spinner=False, # টার্মিনালে লোডিং স্পিনার দেখাবে না
    )

    print("\nশুনছি...")
    
    # ব্যাকগ্রাউন্ডে শোনা শুরু করার জন্য recorder.start() কল করা হচ্ছে
    recorder.start()

    try:
        # প্রোগ্রামটি সচল রাখার জন্য একটি অনন্ত লুপ
        # মূল থ্রেডকে চালু রাখে, যখন ব্যাকগ্রাউন্ড থ্রেড কথা শোনে
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nপ্রোগ্রামটি বন্ধ করা হচ্ছে...")
    finally:
        # প্রোগ্রাম বন্ধ করার সময় রিসোর্স ক্লিন আপ করা হচ্ছে
        recorder.shutdown()
