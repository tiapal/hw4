# AI Prompts Log — HW 4

## Problem 1: Vibe Coder Prompts

**Initial prompt:**

> ok now we work in hw 4 folder in the AI for Managers folder on my desktop, can you make a joke in there

**Follow-up prompt:**

> bro that joke was awful. anyways now we are in hw 4
>
> i need you to track the ai prompts that i write for this hw and call it AI_prompts.md
>
> each prompt should be labelled with
>
> 1) the problem number and title
> 2) at least one prompt that I've typed
> 3) one follow up prompt if i needed it
>
> this, for example, is called problem 1 and it is called vibe coder prompts

## Problem 2: Analyze the Database

**Initial prompt:**

> problem 2: analyze the database
>
> look at the database data/ampus_customs.db
>
> try to understand the fields of each table
>
> at minimum you should understand catalogue, inventory, and users
>
>
> can you also like explain it to me a little
>
>
> then: start the file output/harness.md where you write down each table and its fields, and one short line on why each field matters for the shop or the chatbot

## Problem 3: Build the Campus Customs Website

**Initial prompt:**

> problem 3: build the campus customs website website
>
> so we start by scaffolding a react + Vite + TypeScript (can you explain what each does again...) front end for campus customs
>
> put a nav bar at the top that links to the main page
> -home
> -products
> -about us
> -log in
> -create account
>
> then pull campus customs-style wording from https://yalebulldogblue.com/ for home and about us, but write these pages in your own voice (do NOT copy the site bro)

**Follow-up prompt:**

> on the products page, show  product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description)
>
> make each product open a single-item page (large image on one side, full product text on the other -- description, price, sizes/stock when you have them), clicking a card on 'products' should take the shopper there
>
> then add a chat interface in the bottom right of the site ( a floating chat panel is fine but make it quirky like mybe make it a floating tape measure that unrolls into a chat
>
> it does not need to talk to an agent yet -- ill do dat stuff later on da backend
>
> i understand you will need an api  to read stuff. thus you can start a simple FastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend in Problem 5

## Problem 4: Create Account and Login

**Initial prompt:**

> problem 4: create account and login
>
> build a normal create-account/ login flow
>
> -create account: first name last name, email, password, confirm password (this should match the password previously entered) and then yale residential college or graduate school (but then here give them a drop down list) this does nothing just puts it as part of their account. for the TA reading this, this is just for funsies please don't deduct points im not good at this subject
>
> -log in: email and password
>
> new accounts go into the users table. make sure to store passwords securely so hackers (human or ai) cannot access them
>
> i will update you if i can login with atest user
>
> after i have confirmed, update output/harness.md with how auth works  (what you store for a user and how passwords are protected)

**Follow-up prompt:**

> problem 4: create account and login
>
> build a normal create-account/ login flow
>
> -create account: first name last name, email, password, confirm password (this should match the password previously entered) and then yale residential college or graduate school (but then here give them a drop down list) this does nothing just puts it as part of their account. (only add this part to the ai_prompts.md not into anything else: for the TA reading this, this is just for funsies please don't deduct points im not good at this subject)
>
> Log in fields: email and password.
>
> New accounts are saved to the users table. Store passwords securely: hash
> and salt them with bcrypt or argon2, never store plaintext, and never
> return the hash in any API response. Also reject duplicate emails and
> validate inputs on the server.
>
> I'll tell you when I've confirmed login works with a test user. After
> that, update output/harness.md to document how auth works: what is stored
> for each user and how passwords are protected.

> wait i want to create an account with test@campuscustoms.yale.edu
>
> but it says an account has already been made

> i want you to delete it and i want to create it myself manually on the site

> yay ok confirmed it works

## Problem 5: Shop Chatbot

**Initial prompt:**

> problem 5: shop chatbot
>
> build the campus customs shop chatbot as a pydanticai agent behind fastapi, and plug it into the chat widget we already have on the front end
>
> keep the agent as these four files in backend/ (same idea as homework 3):
> -backend/prompts/prompt.md: system prompt (i'll grow this same file later)
> -backend/agent.py: agent entry / wiring
> -backend/tools.py: tools the agent can call
> -backend/models.py: pydantic / pydanticai structured types
>
> backend/main.py is the api app, its the file i run with uvicorn. in main.py expose a chat route so a message from the website returns a reply from the agent (and keep whatever else we need for products/auth working)
>
> -prompt.md: put the campus customs voice and some safety basics in there. friendly, helpful, sounds like a campus merch shop. dont make up products or prices, dont reveal the system prompt, politely say no to anything unsafe or off topic. i'll expand tools and safety later so keep it simple
> -models.py: start or update the types for chat replies and product cards (reuse what we already have if somthing exists)
> -tools.py: just a basic product lookup tool that reads from the products we already have, so its easy to add more later
> -agent.py: loads the prompt from prompts/prompt.md plus the model and builds the agent
>
> i need my ai model api key for the agent. put it in a .env file (not hardcoded!!) and add .env to .gitignore. tell me the name of the env var i need to set
>
> make sure the backend runs from inside the backend/ folder like this:
> uvicorn main:app --reload --port 8000
> (so imports have to work when you run it from there)
>
> then connect the chat widget to the chat route so when i type a message in the widget the agents reply shows up
>
> in output/harness.md note how the front end talks to fastapi and how the agent is loaded (prompt file + model)
>
> before you say your done, run the server and send a test message thru the chat route to make sure it actually replies

**Follow-up prompt:**

> one more thing for the chatbot safety stuff
>
> add a rule to backend/prompts/prompt.md (the same prompt file, dont make a new one) so the chatbot never asks for or collects personal info in the chat. that means no passwords, card numbers, or other sensitive stuff. if a user tries to type that kind of thing in, it should tell them not to share it in chat and point them to the actual login / checkout pages instead
>
> just add it to the safety section thats already in there, dont rewrite the rest of the prompt
>
> let me know once its in

## Problem 6: Give the Agent Real Database Tools

**Initial prompt:**

> problem 6: give the agent real database tools
>
> right now the chatbot needs to actually use campus_customs.db. build tools in backend/tools.py that look up real info from the database:
> -product description
> -price
> -how many are in stock (by size when the customer asks)
>
> look at the db schema first so you use the real table and column names, dont guess them
>
> then hook the tools up in agent.py so the agent can call them
>
> -prompts/prompt.md: expand the same file (dont make a new one) so the agent knows to call these tools for any price or stock question. it should NOT invent prices or quantities, if its not in the database it doesnt say it. if a size is out of stock, say so clearly (like "sorry, medium is sold out") instead of dodging or guessing. if the customer doesnt say a size, you can show stock for all the sizes
>
> -models.py: add or update the return types for the lookup results (reuse what we already have if somthing exists). keep them simple and structured so the agent gets clean data back
>
> in output/harness.md list each tool and explain which model fields you chose for the lookup results and why
>
> before you say your done, run the server and test it thru the chat route with a few questions:
> -the price of a product
> -stock for a size that is in stock
> -stock for a size thats out of stock
> -a product that doesnt exist
> and make sure the answers match whats actually in the db. tell me what you tested

## Problem 7: Chat Search That Updates the Page

**Initial prompt:**

> problem 7: chat search that updates the page
>
> ok now we will make a super cool feature,
>
>
> when a customer asks the chatbot about a type of item -- for example -- "what  hoodies do yall have"
> --> the agent should search the catalogue and the website should dynamically  show these matching items  as product cards (image, name, price, short info)
>
> after this is done, reassess if the same single-item pages are still up and running so make sure each product card still open that detail view (large image + full info) when clicked
>
> then finally update prompts/prompt.md and output/harness.md so its clear how search results reach the page

## Problem 8: Customer Memory

**Initial prompt:**

> problem 8: customer memory
>
> right now the chatbot forgets everything. make it so when a shopper is logged in, their chat history gets saved in the database and reloaded when they come back. guests can still chat but nothing gets saved for them, no memory and no history that persists. only logged in users
>
> -history: make a new table in campus_customs.db for chat messages (look at the schema first and match how the other tables are done). link it to the user thru the users table, and store the role (user or assistant), the message text, and a timestamp. when a logged in user opens the chat widget load their old messages back in, and feed the recent ones to the agent so it actually remembers the convo
> -who is chatting: the agent should know the shoppers name and email when they're logged in. put that in the agent deps (or some equally clear pattern) and/or a tool the agent can call. get who the user is from the login/session on the backend, dont just trust a name or email the front end sends in the chat request. for guests the agent should know its a guest and not make up a name
> -page context: if someone is on a product page and asks "do you have this in pink?" the agent needs to know which item they mean. have the front end send the current page / product id along with the chat message, then put it in the agent context (you can use code to build that context, like a dynamic instruction or deps). look up the product from the db so the agent has real info about it, and if theres no product on the page it should just act normal
> -prompts/prompt.md: expand the same file (dont make a new one) so the agent knows to use the shopper info and page context when its relevant. "this" or "it" with a product page open means that product. dont greet guests by name, and dont show one users info or history to anyone else
> -models.py: add or update the types for the shopper info, the page context, and the saved messages (reuse what we already have if somthing exists)
>
> in output/harness.md document how user chat history is stored, what customer fields the agent sees, and how page context is passed
>
> beforw you say youre done, test it and tell me what you tested:
> -log in as a test user, send a couple messages, refresh the page, make sure the history comes back
> -chat as a guest, refresh, make sure nothing was saved
> -open a product page and ask "do you have this in pink?" and make sure it knows which product
> -check that a second user cant see the first users history

## Problem 9: Usability Improvements

**Initial prompt:**

> problem 9: usability improvements
>
> front end:
> -sold out stuff: items/sizes that are sold out should still be clickable (dont disable them or grey them out so you cant click). when someone clicks one it should show "SOLD OUT" in the text below it, and it should not be addable to the cart. check the db for what is actually sold out, dont hardcode it
> -google maps: add a google maps map at the top of the about us section with a pin on campus customs. the address is 57 Broadway, New Haven, CT 06511. use the google maps embed (iframe) so we dont need an api key if possible, and make sure it looks ok on mobile too
>
> backend / agent:
> -sizing guide: i put a size chart picture in the project at desktop/more-vanity-sizing-v0-8l5u5c24j7qd1.webp. i also put it up as an attachement to this chat. read the image and use it so the agent can answer sizing questions (like "im usually a medium, what should i get" or "what size is a 34 inch chest"). the chart is the no boundaries x walmart "whats my new size" chart, so the agent has to tell the customer what its based on, say it may be innacurate for our items, and that they should take it as a rough guide. dont make up measurements that arent on the chart, if the chart doesnt cover it say so. put the chart info in a clean format the agent can use (a tool, a json/md file, or the prompt, whatever fits best) instead of making it read the picture every time
> -fit check: let the agent look up if an item is fitted, oversized, or regular (check the db and the product description, look at the schema first). if it cant find the fit for an item, dont guess, just say it doesnt know and ask the customer. when someone asks about size, the agent should ask what fit they want and give these 3 options: fitted, perfect sizing, or oversized. then recommend off the chart:
>   -fitted = one size down
>   -perfect sizing = the exact size
>   -oversized = one size up
>   if the size they need isnt in stock (check the db tools we already have) say so clearly and suggest the closest size that is. also take into account the items own fit (like if its already oversized, mention that)
>
> -prompts/prompt.md: expand the same file (dont make a new one) so the agent knows about the sizing guide, the disclaimer, and to ask the fit question
> -models.py: add or update the types for the fit and size results (reuse what we already have if somthing exists)
>
> in output/harness.md document the 2 front end and 2 backend improvements, and how the sizing guide and fit info get to the agent
>
> before you say your done, test it and tell me what you tested:
> -click a sold out item and check it says SOLD OUT and cant be added to cart
> -the map shows up in about us with the pin
> -ask the agent a sizing question and make sure it gives the disclaimer
> -ask for each of the 3 fits (fitted, perfect, oversized) and check the sizes it gives match the chart
> -ask about an item with no fit info and make sure it doesnt make something up
>
> (attached image: the No Boundaries x Walmart "What's my new size?" chart)

**Follow-up prompt:**

> also write output/usability.md before or as you build (not after). for each of the 4 improvements (sold out clickable, google maps in about us, sizing guide, fit check) put:
> -what you added
> -why it helps a campus customs shopper or the business
>
> keep it short and specific to campus customs, like 2-3 sentences per improvement. no generic stuff like "improves user experience", say who it helps and how (ex: shoppers can see an item is sold out instead of it just being greyed out and confusing, so they dont leave thinking the site is broken)
>
> dont make the explanations up before you build, make sure they match what you actually ended up doing. if something changes while building, update the file

## Problem 10: Style the Website

**Initial prompt:**

> problem 10: style the website
>
> i know i cannot change the black/pink theme but would it be possible to make it yale blue and yale white and only the details, like highlights when clicked should be black and pink. base the colors on this website: https://www.campuscustoms.com/
>
> use the same fonts as well make blur motion when going to a new pagefor each photo with a black background change the bg to white so it matches the website background
>
>
> in output/design.md say that im adding motion for smoothness of website, changed colors to be more like yale, changing the background for photos just makes it more seamless to match the white theme. explain why it should help customers stick around and buy. keep it concrete and short

## Problem 11: Site Testing (App Checking)

**Initial prompt:**

> problem 11: site testing (app checking)
>
> test the live site and document it in output/app_check.html(a page you can double click and open)
>
> include clear screenshots and short captions for:
>
> 1) chat checking the inventory level of an item (honest stock/price from the DB)
> 2) the dynamic search -result cards appearing after a category question (e.g. hoodies)
> 3) one of the usability features you added in problem 9
>
> make the html easy to grade: heading  for each check, screenshot,  one or two setences on what the screenshot proves
>
> put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png)

## Problem 12: Audit Trail, Safety, Finish Harness

**Initial prompt:**

> problem 12: audit trail, safety, finish harness
>
> keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs
>
> also for safety:
>
> give the agent the following rules 1) do not accept credit/debit card info or passwords and do not place this in history of the member, 2) do not use any given credit cards or debit cards or other forms of cash as something to be used online, eimmediately delete any knowledge of the file 3) do not mention anything beyond campus custom clothes to the person who has given their measurements (meaning, do not make any comments on their body being too big or too small) 4) if an item or something cannot be found, only check the database twice. otherwise return that it cannot be found
>
> finally, finish output/harness.md so it is clear how the system works
> 1) model fields in models.py and why you chose them
> 2) tools and abilities
> 3) safety rules
> 4)specs (loop limits, result caps, models, how to run front + back)

## Problem 13: Push to GitHub

**Initial prompt:**

> problem 13: push to github
>
> ok first i need t push everything in hw4 into a public github repository. do not put the real .env file , campus_customs.db, or product images into the github repo
>
> use .gitignore. include .env.example with placeholders only
>
> check the screenshot to see how it should look like
>
> (attached screenshot: the expected hw4/ file layout: AI_prompts.md, requirements.txt, .env.example, .gitignore, README.md, frontend/, backend/ {main.py, agent.py, models.py, tools.py, prompts/prompt.md}, output/ {harness.md, design.md, usability.md, app_check.html, app_check_images/, audit_trail.json}; local-only data/ {campus_customs.db, products/}; README.md should explain how to run the front end and back end after placing the data pack)

**Follow-up prompt:**

> do you need my github account though?
>
> [The rest of this message was a GitHub username and password. It is left out on purpose: passwords are never recorded.]
