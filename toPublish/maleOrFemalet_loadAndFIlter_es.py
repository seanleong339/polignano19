def generateMFEs(outputPath, inputPath):

    import os
    ####[{'col': 0, 'mapping': [('human', 1), ('bot', 2)]}]####

    pathEn = inputPath+"/es"
    human_file = outputPath+"/toDoHumanEs/listHumans.csv"
    w2v = "/media/data/cc.es.300.vec"
    model_fm = '/media/data/MF.weights.06-0.70314-0.68000_fasttext_esp_hb.hdf5'
    results_path = outputPath+"/es/"

    import keras
    model = keras.models.load_model ( model_fm )
    model.summary ( )

    import pandas as pd
    import xml.etree.ElementTree as ET

    def iter_docs(author):
        '''This function extracts the text and the language from the XML'''
        author_attr = author.attrib
        for doc in author.iter('document'):
            doc_dict = author_attr.copy()
            doc_dict.update(doc.attrib)
            doc_dict['data'] = doc.text
            yield doc_dict

    import time

    # Creating empty dataframe
    dataEn = pd.DataFrame()

    # Monitoring time to load the files
    start = time.time()

    for root, dirs, files in os.walk(pathEn):
        for file in files:
            if file == 'truth.txt' or file == 'truth-dev.txt':
                continue
            else:
                try:
                    pathToFile = root + '/' + file # Creating path
                    # print(pathToFile) # Just for debugging
                    xml_data = open(pathToFile, "r", encoding="utf8") # Opening the text file
                    etree = ET.parse(xml_data) # Create an ElementTree object
                    data = list(iter_docs(etree.getroot())) # Create a list of dictionaries with the data
                    filename = file.split(".")[0] # Get filename
                    for dictionary in data: # Loop through the dictionary
                        dictionary['ID'] = filename # Append filename
                    dataEn = dataEn.append(data)  # Append the list of dictionary to a pandas dataframe

                # If the file is not valid, skip it
                except ValueError as e:
                    print(e)
                    continue

    end = time.time()
    print("Total running time is", end - start)

    authorsToCheck = pd.read_csv(human_file, header = None, names = ["ID"])
    mergedEnData = pd.merge(dataEn, authorsToCheck, on='ID')



    '''Creo la litsa degli ID, delle classi e dei tweets pr ogni ID'''
    listaIds =[]
    matrixTweets = []

    for index, x in mergedEnData.iterrows():
        id = x['ID']
        if id not in listaIds:
            newList = list()
            newList.append(x[1])
            matrixTweets.append(newList)
            listaIds.append(id)
        else:
            ls = matrixTweets[listaIds.index(id)]
            ls.append(x[1])
            matrixTweets[listaIds.index(id)] = ls

    print(len(listaIds))

    import gc
    dataEn = None
    target = None
    mergedEnData= None
    gc.collect()



    from ekphrasis.dicts.emoticons import emoticons
    from ekphrasis.classes.preprocessor import TextPreProcessor
    from ekphrasis.classes.tokenizer import SocialTokenizer

    text_processor = TextPreProcessor (
        # terms that will be normalized
        normalize=[ 'email' , 'percent' , 'money' , 'phone' ,
                    'time' , 'url' , 'date' , 'number' ] ,
        fix_html=True ,  # fix HTML tokens
        segmenter="twitter" ,
        corrector="twitter" ,
        unpack_hashtags=True ,  # perform word segmentation on hashtags
        unpack_contractions=False ,  # Unpack contractions (can't -> can not)
        spell_correct_elong=False ,  # spell correction for elongated words
        tokenizer=SocialTokenizer(lowercase=True).tokenize,
        dicts=[ emoticons ]
    )


    import gensim
    google_300 = gensim.models.KeyedVectors.load_word2vec_format(w2v)

    import numpy as np
    from nltk.corpus import stopwords
    import random as rn
    stop_words = set(stopwords.words('english'))


    numFolds = len( matrixTweets ) // 500
    size = 500

    for fold in range(0,numFolds+1):

        indiceInizio = size * fold
        indiceFine = indiceInizio + size
        if indiceFine > len(matrixTweets):
            size = len(matrixTweets) - indiceInizio
            indiceFine = len(matrixTweets)


        i = 0
        matrixTweetsEmb = np.zeros ( (size , 100 , 50 , 300) )
        for tweetsUser in matrixTweets[ indiceInizio:indiceFine ]:
            embTweetsUser = []
            if(i % 100) == 0:
                 print(i)
            for tweet in tweetsUser:
                embTweetUser = np.zeros([50,300])
                #Preprocesso
                tokList = text_processor.pre_process_doc(tweet)
                #Rimuovo le stopwords
                tokList = [w for w in tokList if not w in stop_words]
                #trovo l'embedding
                numTok = 0;
                for token in tokList[0:50]:
                    g_vec =[]
                    is_in_model = False
                    if token in google_300.vocab.keys ( ):
                        is_in_model = True
                        g_vec = google_300.word_vec(token)
                    elif token == "<number>":
                        is_in_model = True
                        g_vec = google_300.word_vec( "número")
                    elif token == "<percent>":
                        is_in_model = True
                        g_vec = google_300.word_vec("porcentaje")
                    elif token == "<money>":
                        is_in_model = True
                        g_vec = google_300.word_vec("dinero")
                    elif token == "<email>":
                        is_in_model = True
                        g_vec = google_300.word_vec("email")
                    elif token == "<phone>":
                        is_in_model = True
                        g_vec = google_300.word_vec("teléfono")
                    elif token == "<time>":
                        is_in_model = True
                        g_vec = google_300.word_vec("hora")
                    elif token == "<date>":
                        is_in_model = True
                        g_vec = google_300.word_vec("fecha")
                    elif token == "<url>":
                        is_in_model = True
                        g_vec = google_300.word_vec("link")
                    elif not is_in_model:
                        max = len ( google_300.vocab.keys ( ) ) - 1
                        index = rn.randint ( 0 , max )
                        word = google_300.index2word[ index ]
                        g_vec = google_300.word_vec( word )

                    embTweetUser[numTok] = np.array(g_vec)
                    numTok += 1
                embTweetsUser.append ( np.array ( embTweetUser ) )
                embTweetUser = None
            matrixTweetsEmb[ i ] = np.array ( embTweetsUser )
            i += 1
            embTweetsUser = None
            gc.collect ( )

        print(matrixTweetsEmb.shape)



        predicted = model.predict(matrixTweetsEmb)

        res = [ '0' ] * len ( matrixTweetsEmb )
        i = 0
        for cl in predicted:
            res[ i ] = str ( np.argmax ( cl ) )
            i += 1

        import shutil
        #[{'col': 0, 'mapping': [('female', 1), ('male', 2)]}]
        def save_to_xml(results,ids):
                path = human_file

                '''This method create an XML with the information of the predictions
                according to the output of the model'''
                for index, x in enumerate(ids):
                    result = results[index]

                    author = ET.Element("author")
                    author.set("id",x)
                    author.set("lang","es")
                    if(result == '0'):
                        author.set("type","human")
                        author.set("gender","female")
                        tree = ET.ElementTree(author)
                        p = results_path+x+".xml"
                        os.makedirs(os.path.dirname(p), exist_ok=True)
                        tree.write(results_path+x+".xml")
                        #print(x," ",female)
                    else:
                        author.set("type","human")
                        author.set("gender","male")
                        tree = ET.ElementTree(author)
                        p = results_path+x+".xml"
                        os.makedirs(os.path.dirname(p), exist_ok=True )
                        tree.write(results_path+x+".xml")
                        #print(x," ",male)

                shutil.rmtree(os.path.dirname(path), ignore_errors=True)
                return

        save_to_xml(res,listaIds[indiceInizio:indiceFine])
        matrixTweetsEmb = None
        res = None
        gc.collect()