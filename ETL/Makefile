.PHONY: install clean reinstall bronze silver gold update-silver-posts

install:
	bash bin/set_env.sh

clean:
	conda env remove -y -n etl

reinstall: clean install

bronze:
	PYTHONPATH=.. python main_bronze.py

silver:
	PYTHONPATH=.. python main_silver.py

gold:
	PYTHONPATH=.. python main_gold.py

update-silver-posts:
	PYTHONPATH=.. python main_update_silver_posts.py
