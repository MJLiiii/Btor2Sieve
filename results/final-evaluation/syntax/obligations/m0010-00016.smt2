(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x497 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x2625 (bvnot ?x497)))
 (let ((?x216 (bvand (_ bv1 1) ?x2625)))
 (not (= ?x216 (_ bv1 1)))))))
(assert
 (let ((?x5502 (select s_11 i_6)))
(let (($x257 (and (distinct ?x5502 (_ bv4294967295 32)) true)))
(not $x257))))
(check-sat)
