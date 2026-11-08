(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x1875 (bvor (bvshl i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
 (let ((?x258 (ite (and (distinct ?x1875 i_4) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x258 (_ bv1 1))))))
(assert
 (let ((?x1875 (bvor (bvshl i_4 (bvurem (_ bv0 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv0 3) (_ bv3 3)))))))
(let (($x142 (bvule ?x1875 (_ bv1 3))))
(not $x142))))
(check-sat)
