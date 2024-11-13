PORT=$1
if [ -z "${PORT}" ]; then
	PORT=40011
fi

cd ../
python3 master_data_collect_ath_social.py --user-name $(whoami) \
	--stack-name sinan-socialnet \
	--min-users 4 --max-users 24 --users-step 2 \
	--exp-time 60 --measure-interval 1 --slave-port $PORT --deploy-config cc_social.json \
	--mab-config social_mab.json --deploy
