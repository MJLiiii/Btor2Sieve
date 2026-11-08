(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x211 (bvuge i_4 (_ bv1 3))))
(not $x211)))
(check-sat)
