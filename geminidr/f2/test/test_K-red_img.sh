name=F2/K-red/raw

# Source a couple of helper functions etc.:
script_dir=$(cd $(dirname "$0"); pwd)
. "$script_dir/../../gemini/test/sh_functions"

start_test_set "$name"

# GS-2018A-DD-101-2:
"$script_dir/reduce_img.sh" "$name" "S2018(0303|0207)S" "S20180211S" 25 || nerr=${nerr}1

end_test_set "$name" $nerr

