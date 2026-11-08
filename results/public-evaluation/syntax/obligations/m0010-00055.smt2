(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x1532 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x2234 (bvnot ?x1532)))
 (let ((?x617 (bvand (_ bv1 1) ?x2234)))
 (not (= ?x617 (_ bv1 1)))))))
(assert
 (let (($x1043 (= i_6 (_ bv255 8))))
(not $x1043)))
(check-sat)
