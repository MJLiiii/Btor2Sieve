(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x1034 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x16 (bvnot ?x1034)))
 (let ((?x536 (bvand (_ bv1 1) ?x16)))
 (not (= ?x536 (_ bv1 1)))))))
(assert
 (let (($x1353 (and (distinct i_6 (_ bv0 8)) true)))
(not $x1353)))
(check-sat)
