import json, urllib.request, time, os, sys
S = """Halo semuanya, selamat datang di live kali ini.
Aku Selena, senang banget bisa ketemu kalian semua hari ini.
Hari ini cuacanya cerah, cocok buat jalan-jalan sore.
Kamu lagi ngapain sekarang? Jangan lupa makan ya.
Aku suka banget nyanyi, apalagi kalau lagunya bikin semangat.
Terima kasih ya sudah mampir, jangan lupa tekan tombol suka.
Eh tunggu dulu, kok tiba-tiba layarnya gelap sih?
Wah, hebat sekali! Aku nggak nyangka kamu bisa sampai sini.
Pelan-pelan aja, nggak usah buru-buru, aku tungguin kok.
Malam ini kita santai aja, sambil dengerin musik bareng.
Kalau kamu capek, istirahat dulu sebentar, minum air putih.
Ayo kita mulai permainannya, siapa yang paling cepat dia menang!
Hmm, aku lagi mikir, enaknya lagu apa ya yang dinyanyiin sekarang?
Jangan nakal ya, nanti aku marah beneran lho.
Besok pagi aku bangun lebih awal supaya bisa olahraga dulu.
Ceritanya panjang banget, tapi seru, kamu pasti suka.
Aku nggak bisa berhenti ketawa, lucu banget tadi.
Tolong bantu aku pilih warna baju yang paling cocok dong.
Langit senja itu indah sekali, warnanya oranye keemasan.
Setiap hari adalah kesempatan baru untuk jadi lebih baik.
Dengarkan baik-baik, ini bagian favoritku dari seluruh lagu.
Dulu aku takut tampil di depan banyak orang, sekarang sudah biasa.
Kamu pernah nggak ngerasa kangen sama sesuatu yang nggak bisa kembali?
Hujan turun pelan, suaranya bikin tenang, aku suka.
Ayo tepuk tangan yang meriah untuk semua yang hadir malam ini!
Satu, dua, tiga, mulai! Ikuti iramanya ya.
Aku janji bakal berusaha sebaik mungkin, tapi bantu aku juga ya.
Kenapa sih dunia ini rumit banget, padahal tinggal bahagia aja.
Pelukan hangat buat kamu yang lagi sedih hari ini.
Di kejauhan terdengar suara ombak yang memecah di pantai.
Jangan menyerah, setiap usaha pasti ada hasilnya suatu hari nanti.
Wah, ramai sekali ya, terima kasih sudah datang semuanya.
Ssst, dengerin deh, ada suara aneh dari luar jendela.
Rasanya seperti mimpi, bisa nyanyi bareng kalian semua di sini.
Namaku Selena, dan ini panggung kecilku yang paling kusayang.
Lagu ini aku persembahkan khusus buat kalian yang setia nonton.
Kita lanjut ke segmen berikutnya, siap-siap ya.
Coba tebak, hari ini aku dapat kabar gembira apa?
Aduh, aku salah ngomong, maaf ya, ulang lagi deh.
Bintang-bintang bersinar terang di langit malam yang tenang.
Mari kita bernyanyi bersama, angkat tangan kalian tinggi-tinggi!
Kalau hatimu sedang gundah, dengarkan saja lagu ini pelan-pelan.
Aku suka kopi hangat di pagi hari, apalagi kalau ditemani roti.
Perjalanan ini panjang, tapi bersama kalian rasanya jadi ringan.
Percayalah, semua akan indah pada waktunya, tinggal sabar sedikit lagi.
Wow, keren banget! Bagaimana kamu melakukannya?
Tidak ada yang mustahil kalau kita mau berusaha dan berdoa.
Kenangan itu seperti lagu lama yang selalu enak didengar.
Hati-hati di jalan ya, kabari aku kalau sudah sampai rumah.
Aku akan selalu ada di sini, menemani kalian sampai akhir.
Selamat malam, mimpi indah, sampai jumpa lagi besok.""".split('\n')
out = 'ref'; tot = 0
for i, s in enumerate(S):
    p = f'{out}/s{i:03d}.wav'
    if os.path.exists(p): continue
    try:
        r = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:6001/tts', data=json.dumps({'text': s, 'voice': 'selena_zenith'}).encode(), headers={'Content-Type': 'application/json'}), timeout=90)
        open(p, 'wb').write(r.read())
    except Exception as e: print('gagal', i, str(e)[:60])
print('selesai', len(os.listdir(out)), 'file')
