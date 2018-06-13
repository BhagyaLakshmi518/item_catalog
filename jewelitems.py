from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jewel_db import Jewellery, Base, JewelItem, User

engine = create_engine('sqlite:///Jewellery.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

# Menu for UrbanBurger
restaurant1 = Jewellery(user_id=1, name="Sonam Jewels")

session.add(restaurant1)
session.commit()

Item2 = JewelItem(user_id=1, name="earrings", description="an ornament attached to ear with a stone",
                     price="$7.50", jewellery=restaurant1)

session.add(Item2)
session.commit()


Item1 = JewelItem(user_id=1, name="hat pin", description="used for decoration of hat",
                     price="$2.99", jewellery=restaurant1)

session.add(Item1)
session.commit()

Item3 = JewelItem(user_id=1, name="hair pin", description="Used to decorate hair",
                     price="$5.50", jewellery=restaurant1)

session.add(Item3)
session.commit()



# Menu for Super Stir Fry
restaurant2 = Jewellery(user_id=1, name="Royal Palace")

session.add(restaurant2)
session.commit()


Item1 = JewelItem(user_id=1, name="Necklaces", description="Ornament for neck",
                     price="$7.99", jewellery=restaurant2)

session.add(Item1)
session.commit()

Item2 = JewelItem(user_id=1, name="anklets",
                     description="a jewel for anklets for a traditional look", price="$25", jewellery=restaurant2)

session.add(Item2)
session.commit()

Item3 = JewelItem(user_id=1, name="Bangles", description="an ornament for hands",
                     price="$15", jewellery=restaurant2)

session.add(Item3)
session.commit()



print ("added menu items!")
