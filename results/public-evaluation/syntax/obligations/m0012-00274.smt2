(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x583 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x1089 (bvor (bvlshr i_4 (bvurem (_ bv1 3) (_ bv3 3))) (bvshl i_4 (bvsub (_ bv3 3) (bvurem (_ bv1 3) (_ bv3 3)))))))
 (let ((?x211 (ite (and (distinct ?x1089 ?x583) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x211 (_ bv1 1)))))))
(assert
 (let (($x2932 (and (distinct i_4 (_ bv7 3)) true)))
(not $x2932)))
(check-sat)
