(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x763 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x944 (bvnot ?x763)))
 (let ((?x47 (bvand (_ bv1 1) ?x944)))
 (not (= ?x47 (_ bv1 1)))))))
(assert
 (let ((?x1080 (select s_11 i_6)))
(let ((?x288 ((_ extract 7 0) ?x1080)))
(let (($x6949 (bvule (_ bv200 8) ?x288)))
(let (($x973 (or (not (= ((_ extract 31 8) ?x1080) (_ bv0 24))) $x6949)))
(let (($x3122 (not $x973)))
(let (($x1885 (not $x3122)))
(not $x1885))))))))
(check-sat)
