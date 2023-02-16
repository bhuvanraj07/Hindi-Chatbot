#pip install googletrans==3.1.0a0


from googletrans import Translator
translator = Translator(service_urls=['translate.google.com','translate.google.co.kr',])

translator = Translator()
translation = translator.translate("main bahot dukhi ho gya hoon ji is zindagi se", dest='en')
print(translation.text)
