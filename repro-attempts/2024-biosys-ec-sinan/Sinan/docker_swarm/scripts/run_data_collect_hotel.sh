cd ../
python3 master_data_collect_ath_hotel.py --user-name $(whoami) \
	--stack-name hotelreservation \
	--min-users 2 --max-users 48 --users-step 1 \
	--exp-time 750 --measure-interval 1 --slave-port 40011 --deploy-config hotel_cluster.json \
	--mab-config hotel_mab.json --deploy