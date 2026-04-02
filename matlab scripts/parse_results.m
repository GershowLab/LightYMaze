function [expt] = parse_results(results_f_name)


if exist(results_f_name, "dir")
    d = dir(fullfile(results_f_name, '*results.csv'));
    for j = 1:length(d)
        expt(j) = parse_results(fullfile(d(j).folder, d(j).name));
    end
    return
end

if ~exist(results_f_name, 'file')
    expt = [];
    return
end
opts = detectImportOptions(results_f_name);
opts = setvartype(opts, 'Message', 'char');
results = readtable(results_f_name, opts);
decision_ind = find(strncmpi(results.Message, 'CONF',4));
led_on(1,:) = results.Led1B > 0;
led_on(2,:) = results.Led2B > 0;
led_on(3,:) = results.Led3B > 0;

for j = 1:length(decision_ind)
    ii = decision_ind(j);
    decision(j).mazeID = results.MazeID(ii);
    decision(j).time = results.FrameTime(ii);
    decision(j).frame = results.Frame(ii);
    decision(j).to_channel = sscanf(results.Message{ii}, 'CONF%d');
    decision(j).to_light = led_on(decision(j).to_channel, ii-1);
    decision(j).to_dark = ~led_on(decision(j).to_channel, ii-1) && any(led_on(:,ii-1));
    decision(j).no_light = ~any(led_on(:,ii-1));
end

for j = 1:max([decision.mazeID])
    d = decision([decision.mazeID] == j);
    maze(j).num_to_channel = histcounts([d.to_channel], [1 2 3 4]);
    maze(j).num_to_light = nnz([d.to_light]);
    maze(j).num_to_dark = nnz([d.to_dark]);
    maze(j).num_no_light = nnz([d.no_light]);
    maze(j).frac_to_light = maze(j).num_to_light / (maze(j).num_to_light + maze(j).num_to_dark);
end

expt.fname = results_f_name;
expt.results = results;
expt.decision = decision;
expt.maze = maze;
expt.frac_to_light = nnz([decision.to_light])/(nnz([decision.to_light] | [decision.to_dark]));
nbin = 10;
txe = linspace(expt.results.FrameTime(1), expt.results.FrameTime(end), nbin+1);
bin = discretize([decision.time], txe);
for j = 1:nbin
    d = decision(bin == j);
    expt.tx(j) = mean([d.time]);
    expt.n_to_light_vs_time(j) = nnz([d.to_light]);
    expt.n_to_dark_vs_time(j) = nnz([d.to_dark]);
end
expt.frac_to_light_vs_time = expt.n_to_light_vs_time./(expt.n_to_light_vs_time + expt.n_to_dark_vs_time);



end