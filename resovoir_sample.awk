#! /usr/bin/awk -f

# resovoir_sample.awk

# the basic resovoir algorithm is due to Alan Waterman (according to Knuth)
# Vitter (85) improved timing and made sampling uniform
# http://www.cs.umd.edu/~samir/498/vitter.pdf
#
# Expect a K parameter which is the size of the intended sample
#
# resovoir_sample.awk -v K=1000   population.list


BEGIN {
	 # give srand a fixed seed for reproducubility
	 # or a variable for diversity
	 srand(systime() + PROCINFO["pid"]);

	# 23 is a magic number between 10 & 40 as per Vitter
 	threshold = 23 * K;
}


# fill the resovoir
NR <= K {	resovoir[NR] = $0 }

# replace item in resovior with current item
# on probability of K / (NR)
NR > K {
	uniform_probability = int(rand() * NR + 0.5);
	if (uniform_probability  <= K)
		resovoir[uniform_probability] = $0

	# when the population is large with respect to sample size K
	# test fewer items from the population for inclusion in the resovoir
	#if(NR < threshold){
	#	skip =
	#	for (i=0 ; i < skip; i++) getline()
	#}
}

# and Bobs yer uncle
END {	for(item in resovoir) {print resovoir[item]} }

# without the progressivly larger steps through the population
# this would not approach uniform since for larger the populations
# more earlier candidates are replaced than later candidates.
