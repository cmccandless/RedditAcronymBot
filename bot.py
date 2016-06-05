#!/usr/bin/python

from lxml import html 
import requests, re, sys, praw, OAuth2Util

#Settings
user_agent='Finds and replies with acronym definitions; Dev: /u/pastrygeist'
footer = u'*This bot is new and may be prone to some bugs. PM /u/pastrygeist with suggestions or bugs before banning.*'
urlTemplate='http://www.acronymfinder.com/{1}{0}.html' 
meaningLimit=3
contextKeywords={
  (u'military',u'army',u'government',u'navy',u'airforce'):'Military-and-Government/',
}
exclude = []
with open('.exclude') as f:
  exclude = f.read().splitlines()

rgxAcronym=re.compile(r'\b([A-Z]{2,})\b')

def getContext(input):
  inputLower=input.lower()
  for keywords, context in contextKeywords.items():
    for keyword in keywords:
      if keyword in input:
        return context
  return ''

def getUrl(acronym,meaningContext):
  return urlTemplate.format(acronym,meaningContext)

def getMeanings(acronym,context):
  page=requests.get(getUrl(acronym,context))
  tree=html.fromstring(page.content)
  rows=tree.xpath('//table[@class="table table-striped result-list"]/tbody/tr')[:meaningLimit]
  meanings=[]
  for row in rows:
    rank=row.xpath('./td[@class="result-list__body__rank"]/a/@class')[0]
#    if rank!='r5':
#      continue
    resultMeaning=row.xpath('./td[@class="result-list__body__meaning"]')[0]
    meaning = ''
    tmp=resultMeaning.xpath('./text()')
    if len(tmp)>0:
      meaning=tmp[0]
    if meaning=='':
      meaningLink = resultMeaning.xpath('./a')[0]
      meaning = u'[{}]({})'.format(meaningLink.xpath('./text()')[0],meaningLink.xpath('./@href')[0])
    meanings.append(meaning)
  return meanings

def getAcronyms(text,context):
  dict={}
  for acro in rgxAcronym.findall(text):
    if acro in exclude:
      continue
    localContext = context
    meanings=getMeanings(acro,context)
    if len(meanings)==0:
      localContext = ''
      meanings=getMeanings(acro,localContext)
    dict[acro]=(meanings,localContext)
  return dict

def processComment(input):
  context = getContext(input)
  meaningsByAcronym=getAcronyms(input,context)
  keys=meaningsByAcronym.keys()
  if len(keys)==0:
    return "".encode('utf8')
  keys.sort(key=lambda x: input.find(x))
  
  output=u'>{}'.format(input)
  output+=u'\n\nFound the following acronyms:\n\n'
  for acro in keys:
    meanings,localContext = meaningsByAcronym[acro]
    acroText = u'* [{}]({})\n\n'.format(acro,getUrl(acro,localContext))
    output+=acroText
    for meaning in meanings:
      meaningText = u' * {}\n\n'.format(meaning)
      output+=meaningText
    if len(meanings)==0:
      output+=u' * *No meanings found*\n\n'

  output+=footer
  return output.encode('utf8')

def check_condition(c):
  text = c.body
  tokens = text.lower().split()
  if '/u/theacronymbot' in tokens and 'help' in tokens:
    return 1
  elif text.upper()!=text and rgxAcronym.match(text):
    return 2
  return 0

def bot_action(c,condition,verbose=True,respond=False):
  response = u''
  if condition==1:
    response = processComment(c.parent.body)
  elif condition==2:
    response = processComment(c.body)
  else:
    return
  if response=="".encode('utf8'):
    return
  if verbose:
   print(c.permalink)
   print(response)
   print('----------------------------------')
  if respond:
    c.reply(response)

def testit():
  input="""There is actual accountability in the military. Example: Situation occurs and MP strikes somebody in the head for whatever reason. That report goes to 
  the Provost Marshals office, MP's command knows about it, other persons command gets informed, JAG might be informed, MPI or CID might also be involved 
  depending on the situation. So before that MP is even off duty 30+ people know about the event. Somebody WILL fuck you up if you didn't do things right. The 
  thin blue line doesn't exist to the same extant that it does for civilian law enforcement. Please excuse any errors, on mobile.""" 
  output=processComment(input)
  print(output)

r = praw.Reddit(user_agent)
o = OAuth2Util.OAuth2Util(r,print_log=True)
o.refresh(force=True)

url = r.get_authorize_url('uniqueKey','identity',True)
import webbrowser
webbrowser.open(url)

print('My Comment Karma: {}'.format(r.get_me().comment_karma))

while True:
  for c in praw.helpers.comment_stream(r,'askreddit'):
    condition=check_condition(c)
    bot_action(c,condition)

  if len(sys.argv)>0 and '--cron' in sys.argv:
    break
  
  time.sleep(3600)
